import os
import sys
import re
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import logging
from typing import Optional, List
from database import prisma

# Import Masking Service
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from packages.masking.masking import MaskingService
from routers.auth import get_current_user
from services.chiffrement import generate_seed, encrypt_seed, decrypt_seed, mask_seed_for_display
from packages.events import event_bus
from packages.rule_cache import rule_cache
from packages.rule_engine.engine import RuleEngine

router = APIRouter()
masking_service = MaskingService()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: str = "kinga-sim"
    tags: str = ""
    api_keys: Optional[dict] = None

class RuleToggleRequest(BaseModel):
    category: str
    isActive: bool
    level: str = "low"

class CustomRuleRequest(BaseModel):
    pattern: str       # regex pattern
    format: str = ""   # alias format e.g. "[CUSTOM_{n}]"
    category: str = "custom"
    level: str = "low"


# ─── HELPERS ────────────────────────────────────────────────────

async def get_or_create_active_ruleset(org_id: str):
    """Get the active MaskingRuleSet for an org, or create one with a fresh encrypted seed."""
    ruleset = await prisma.maskingruleset.find_first(
        where={"orgId": org_id, "status": "active"},
        order={"version": "desc"},
        include={"rules": True}
    )
    if not ruleset:
        seed = generate_seed()
        encrypted = encrypt_seed(seed)
        ruleset = await prisma.maskingruleset.create(
            data={
                "orgId": org_id,
                "seed": encrypted,
                "status": "active",
                "version": 1,
            },
            include={"rules": True}
        )
        # Seed default rules into the new ruleset
        defaults = ["names", "contact", "finance", "dates", "documents"]
        for cat in defaults:
            await prisma.rule.create(data={
                "category": cat,
                "isActive": True,
                "level": "low",
                "orgId": org_id,
                "ruleSetId": ruleset.id,
            })
        ruleset = await prisma.maskingruleset.find_unique(
            where={"id": ruleset.id},
            include={"rules": True}
        )
    return ruleset


async def verify_org_membership(user, org_id: str, required_roles=None):
    """Verify that user belongs to the given org. Optionally check role."""
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette organisation.")
    if required_roles and membership.role not in required_roles:
        raise HTTPException(status_code=403, detail=f"Rôle requis : {', '.join(required_roles)}")
    return membership

# ─── CHAT ───────────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest, response: Response, user=Depends(get_current_user)):
    # 1. Get user's org
    membership = await prisma.membership.find_first(where={"userId": user.id})
    org = None
    ruleset = None
    if membership:
        org = await prisma.organization.find_unique(where={"id": membership.orgId})

    # 2. Character length check and Token quota check (org-level)
    if len(request.message) > 10000:
        raise HTTPException(status_code=400, detail="Le message dépasse la limite de 10 000 caractères.")

    num_tokens = len(request.message) // 4 + 1
    if org:
        if org.tokenUsed + num_tokens > org.tokenLimit:
            raise HTTPException(status_code=403, detail="Limite de tokens de l'organisation atteinte.")
    
    # 3. Fetch org-scoped active MaskingRuleSet and its rules (Redis Cache first)
    active_rules = {"names": True, "contact": True, "finance": True, "dates": True, "documents": True}
    rule_levels = {"names": "high", "contact": "medium", "finance": "low", "dates": "medium", "documents": "medium"}
    custom_rules = []
    ruleset_version = 1
    
    try:
        if org:
            cached = rule_cache.get(org.id)
            if cached:
                logging.info(f"[Chat] Loaded rules from Redis cache for org {org.id} (v{cached.get('version')})")
                ruleset_version = cached.get("version", 1)
                for r in cached.get("rules", []):
                    if r.get("category") == "custom" and r.get("pattern"):
                        custom_rules.append(r)
                    else:
                        active_rules[r.get("category")] = r.get("isActive")
                        rule_levels[r.get("category")] = r.get("level", "medium")
            else:
                logging.info(f"[Chat] Redis cache miss for org {org.id}. Loading from database.")
                ruleset = await get_or_create_active_ruleset(org.id)
                ruleset_version = ruleset.version
                rules_list = []
                for r in (ruleset.rules or []):
                    rules_list.append({
                        "category": r.category,
                        "isActive": r.isActive,
                        "level": r.level,
                        "pattern": r.pattern,
                        "format": r.format
                    })
                    if r.category == "custom" and r.pattern:
                        custom_rules.append(r)
                    else:
                        active_rules[r.category] = r.isActive
                        rule_levels[r.category] = r.level
                # Populate cache
                rule_cache.set(org.id, ruleset_version, rules_list)
        else:
            # Fallback: load rules without org scope
            rules = await prisma.rule.find_many(where={})
            for r in rules:
                active_rules[r.category] = r.isActive
                rule_levels[r.category] = r.level
    except Exception as e:
        logging.error(f"Rule fetch error: {e}", exc_info=True)

    # Fetch/decrypt seed for organization
    seed = "fallback_default_seed_kinga"
    if org:
        ruleset = await prisma.maskingruleset.find_first(
            where={"orgId": org.id, "status": "active"},
            order={"version": "desc"}
        )
        if not ruleset:
            ruleset = await get_or_create_active_ruleset(org.id)
        if ruleset:
            try:
                seed = decrypt_seed(ruleset.seed)
            except Exception as e:
                logging.error(f"Failed to decrypt seed, using raw: {e}")
                seed = ruleset.seed

    # 4. Apply advanced masking with synthetic dictionaries and custom rules
    start_mask = time.perf_counter()
    masked_message, mapping = masking_service.mask_message(
        text=request.message,
        org_id=org.id if org else "global",
        seed=seed,
        active_rules=active_rules,
        rule_levels=rule_levels,
        custom_rules=custom_rules
    )
    masking_ms = (time.perf_counter() - start_mask) * 1000

    # 5. Dynamic LLM Router (OpenAI / Anthropic / Ollama / Simulator)
    start_llm = time.perf_counter()
    fake_llm_response = ""
    model_name = request.model
    api_keys = request.api_keys or {}

    if model_name == "gpt-4o" and api_keys.get("openai"):
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {api_keys['openai']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": masked_message}]
            }
            with httpx.Client(timeout=30.0) as client:
                res = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                if res.status_code == 200:
                    fake_llm_response = res.json()["choices"][0]["message"]["content"]
                else:
                    fake_llm_response = f"Erreur OpenAI (Code {res.status_code}): {res.text}"
        except Exception as e:
            fake_llm_response = f"Erreur lors de l'appel à OpenAI: {str(e)}"

    elif model_name == "claude-3-5-sonnet" and api_keys.get("anthropic"):
        try:
            import httpx
            headers = {
                "x-api-key": api_keys['anthropic'],
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": masked_message}]
            }
            with httpx.Client(timeout=30.0) as client:
                res = client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
                if res.status_code == 200:
                    fake_llm_response = res.json()["content"][0]["text"]
                else:
                    fake_llm_response = f"Erreur Anthropic (Code {res.status_code}): {res.text}"
        except Exception as e:
            fake_llm_response = f"Erreur lors de l'appel à Anthropic: {str(e)}"

    elif model_name == "llama3-local":
        local_url = api_keys.get("local") or "http://localhost:11434"
        try:
            import httpx
            payload = {
                "model": "llama3",
                "messages": [{"role": "user", "content": masked_message}],
                "stream": False
            }
            # Clean URL
            clean_url = local_url.rstrip("/")
            with httpx.Client(timeout=30.0) as client:
                res = client.post(f"{clean_url}/api/chat", json=payload)
                if res.status_code == 200:
                    fake_llm_response = res.json()["message"]["content"]
                else:
                    fake_llm_response = f"Erreur Ollama (Code {res.status_code}): {res.text}"
        except Exception as e:
            fake_llm_response = f"Erreur lors de l'appel à Ollama ({local_url}): {str(e)}"

    # Fallback to Simulator if no real model responded
    if not fake_llm_response:
        fake_llm_response = f"J'ai bien reçu votre demande concernant : '{masked_message}'. La sécurité Kinga a validé le masquage."

    llm_ms = (time.perf_counter() - start_llm) * 1000

    start_unmask = time.perf_counter()
    unmasked_response = masking_service.unmask_message(fake_llm_response)
    unmask_ms = (time.perf_counter() - start_unmask) * 1000
    
    # 6. Persist with ruleSetId linkage
    conv_id = request.conversation_id
    try:
        if not conv_id:
            conv = await prisma.conversation.create(
                data={
                    "title": request.message[:50] + ("..." if len(request.message) > 50 else ""),
                    "userId": user.id,
                    "orgId": org.id if org else None,
                    "modelUsed": request.model,
                    "tags": request.tags,
                    "ruleSetId": ruleset.id if ruleset else None,
                }
            )
            conv_id = conv.id
            
        await prisma.message.create(data={
            "content": request.message,
            "maskedContent": masked_message,
            "role": "user",
            "tokenCount": num_tokens,
            "modelUsed": request.model,
            "conversationId": conv_id
        })
        await prisma.message.create(data={
            "content": unmasked_response,
            "maskedContent": fake_llm_response,
            "role": "assistant",
            "tokenCount": len(fake_llm_response) // 4 + 1,
            "modelUsed": request.model,
            "conversationId": conv_id
        })
        
        # Deduct tokens and check quotas
        if org:
            new_tokens_used = org.tokenUsed + num_tokens
            await prisma.organization.update(where={"id": org.id}, data={"tokenUsed": new_tokens_used})
            
            # Quota usage checks
            used_ratio = new_tokens_used / org.tokenLimit if org.tokenLimit > 0 else 0
            if used_ratio > 0.8:
                response.headers["X-Quota-Warning"] = f"{int(used_ratio * 100)}%"
                logging.warning(
                    f"Quota warning: Org {org.id} is at {used_ratio * 100:.1f}% capacity.",
                    extra={"org_id": org.id, "user_id": user.id}
                )
            if used_ratio > 0.95:
                await prisma.auditlog.create(data={
                    "action": "quota.warning",
                    "details": f"Alerte : Utilisation critique du quota de tokens à {used_ratio * 100:.1f}%.",
                    "userId": user.id,
                    "orgId": org.id,
                })

        # Structured logging for metrics and observability
        logging.info(
            f"Chat processed successfully for user {user.id}",
            extra={
                "org_id": org.id if org else None,
                "user_id": user.id,
                "conversation_id": conv_id,
                "metrics": {
                    "masking_ms": masking_ms,
                    "llm_ms": llm_ms,
                    "unmask_ms": unmask_ms,
                    "total_chat_ms": masking_ms + llm_ms + unmask_ms,
                    "token_count": num_tokens,
                    "masked_entities_count": len(mapping)
                }
            }
        )

        # Audit log
        await prisma.auditlog.create(data={
            "action": "chat.send",
            "details": f"Masqué {len(mapping)} entité(s). Modèle: {request.model}. RuleSet v{ruleset.version if ruleset else '?'}",
            "userId": user.id,
            "orgId": org.id if org else None,
        })
    except Exception as e:
        logging.error(f"DB save error: {e}", exc_info=True)
    
    return {
        "conversation_id": conv_id,
        "original_message": request.message,
        "masked_message_sent": masked_message,
        "llm_response_masked": fake_llm_response,
        "final_response": unmasked_response,
        "mapping_used": mapping,
        "ruleset_version": ruleset.version if ruleset else None,
    }

# ─── CONVERSATIONS ──────────────────────────────────────────────

@router.get("/conversations")
async def get_conversations(user=Depends(get_current_user), status: str = None, tag: str = None, q: str = None):
    try:
        where = {"userId": user.id}
        if status:
            where["status"] = status
        if tag:
            where["tags"] = {"contains": tag}
        if q:
            where["title"] = {"contains": q}

        conversations = await prisma.conversation.find_many(
            where=where,
            include={"messages": True},
            order={"updatedAt": "desc"}
        )
        return [
            {
                "id": c.id,
                "title": c.title,
                "tags": c.tags,
                "status": c.status,
                "modelUsed": c.modelUsed,
                "created_at": c.createdAt.isoformat(),
                "updated_at": c.updatedAt.isoformat(),
                "message_count": len(c.messages)
            }
            for c in conversations
        ]
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        return []

@router.patch("/conversations/{conv_id}")
async def update_conversation(conv_id: str, user=Depends(get_current_user), tags: str = None, status: str = None):
    update_data = {}
    if tags is not None:
        update_data["tags"] = tags
    if status is not None:
        update_data["status"] = status
    try:
        conv = await prisma.conversation.update(where={"id": conv_id}, data=update_data)
        return {"id": conv.id, "tags": conv.tags, "status": conv.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── DASHBOARD STATS ────────────────────────────────────────────

@router.get("/stats/dashboard")
async def get_dashboard_stats(user=Depends(get_current_user), view: str = "user"):
    try:
        membership = await prisma.membership.find_first(where={"userId": user.id})
        org = None
        if membership:
            org = await prisma.organization.find_unique(where={"id": membership.orgId})

        # Scope based on role
        if view == "admin" and membership and membership.role == "admin" and org:
            msg_where = {"conversation": {"orgId": org.id}}
        elif view == "manager" and membership and membership.role in ("manager", "admin") and org:
            msg_where = {"conversation": {"orgId": org.id}}
        else:
            msg_where = {"conversation": {"userId": user.id}}

        total_requests = await prisma.message.count(where={**msg_where, "role": "user"})
        
        user_messages = await prisma.message.find_many(
            where={**msg_where, "role": "user", "maskedContent": {"not": None}}
        )
        total_masked = sum(len(re.findall(r'\[[A-Z]+_\d+\]', m.maskedContent or "")) for m in user_messages)
        time_saved = f"{round(total_requests * 0.08, 1)}h" if total_requests > 0 else "0h"
        
        # Active users count (org-level for admin/manager)
        active_users = "1"
        if org and view in ("admin", "manager"):
            member_count = await prisma.membership.count(where={"orgId": org.id})
            active_users = str(member_count)

        recent_messages = await prisma.message.find_many(
            where=msg_where,
            include={"conversation": True},
            order={"createdAt": "desc"},
            take=8
        )
        
        recent_logs = []
        for msg in recent_messages:
            if msg.role == "user":
                tokens = re.findall(r'\[[A-Z]+_\d+\]', msg.maskedContent or "")
                recent_logs.append({
                    "title": msg.conversation.title if msg.conversation else "Sans titre",
                    "description": f"Message analysé. {len(tokens)} entité(s) masquées. Modèle: {msg.modelUsed}",
                    "meta": f"{msg.createdAt.strftime('%H:%M')} · {msg.modelUsed}"
                })
                
        if not recent_logs:
            recent_logs = [{"title": "Aucune activité", "description": "Envoyez des messages pour voir l'activité ici.", "meta": "Maintenant"}]

        return {
            "total_requests": str(total_requests),
            "requests_trend": "+12%",
            "total_entities_masked": str(total_masked),
            "avg_entities_per_request": str(round(total_masked / total_requests, 1)) if total_requests > 0 else "0",
            "time_saved": time_saved,
            "active_users": active_users,
            "plan": org.plan if org else "free",
            "tokenLimit": org.tokenLimit if org else 10000,
            "tokenUsed": org.tokenUsed if org else 0,
            "recent_logs": recent_logs,
            "role": membership.role if membership else "member"
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {}

# ─── RULES (ORG-ISOLATED) ───────────────────────────────────────

@router.get("/rules")
async def get_rules(user=Depends(get_current_user)):
    """Fetch rules scoped to the user's org's active MaskingRuleSet."""
    try:
        membership = await prisma.membership.find_first(where={"userId": user.id})
        if not membership:
            return []
        org_id = membership.orgId

        ruleset = await get_or_create_active_ruleset(org_id)

        # Return only rules belonging to this specific ruleset
        rules = await prisma.rule.find_many(
            where={"ruleSetId": ruleset.id},
            order={"updatedAt": "desc"}
        )
        return [
            {
                "id": r.id,
                "category": r.category,
                "isActive": r.isActive,
                "level": r.level,
                "pattern": r.pattern,
                "format": r.format,
                "ruleSetId": r.ruleSetId,
                "updatedAt": r.updatedAt.isoformat(),
            }
            for r in rules
        ]
    except Exception as e:
        print(f"Error fetching rules: {e}")
        return []

@router.post("/rules")
async def update_rule(request: RuleToggleRequest, user=Depends(get_current_user)):
    """Update a standard rule within the user's active org-scoped ruleset."""
    try:
        membership = await prisma.membership.find_first(where={"userId": user.id})
        if not membership:
            raise HTTPException(status_code=403, detail="Organisation requise.")
        org_id = membership.orgId

        ruleset = await get_or_create_active_ruleset(org_id)

        # Find existing rule in THIS ruleset
        existing = await prisma.rule.find_first(
            where={"category": request.category, "ruleSetId": ruleset.id}
        )
        if existing:
            rule = await prisma.rule.update(
                where={"id": existing.id},
                data={"isActive": request.isActive, "level": request.level}
            )
        else:
            rule = await prisma.rule.create(data={
                "category": request.category,
                "isActive": request.isActive,
                "level": request.level,
                "orgId": org_id,
                "ruleSetId": ruleset.id,
            })

        # Increment version & publish event
        new_version = ruleset.version + 1
        await prisma.maskingruleset.update(where={"id": ruleset.id}, data={"version": new_version})
        await event_bus.publish("rule_set.updated", {"organizationId": org_id, "version": new_version})

        # Audit
        await prisma.auditlog.create(data={
            "action": "rule.toggle",
            "details": f"Règle '{request.category}' → {'activée' if request.isActive else 'désactivée'} (niveau: {request.level}) [RuleSet v{new_version}]",
            "userId": user.id,
            "orgId": org_id,
        })
        return {
            "id": rule.id,
            "category": rule.category,
            "isActive": rule.isActive,
            "level": rule.level,
            "ruleSetId": rule.ruleSetId,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rules/template")
async def apply_rule_template(template: str = "default", user=Depends(get_current_user)):
    """Apply a preset rule template scoped to the org's active ruleset."""
    templates = {
        "default": {"names": ("low", True), "contact": ("low", True), "finance": ("low", True), "dates": ("low", True), "documents": ("low", True)},
        "bank": {"names": ("high", True), "contact": ("high", True), "finance": ("high", True), "dates": ("medium", True), "documents": ("high", True)},
        "health": {"names": ("high", True), "contact": ("high", True), "finance": ("low", False), "dates": ("high", True), "documents": ("high", True)},
        "ecommerce": {"names": ("medium", True), "contact": ("high", True), "finance": ("medium", True), "dates": ("low", False), "documents": ("medium", True)},
    }
    tpl = templates.get(template, templates["default"])
    membership = await prisma.membership.find_first(where={"userId": user.id})
    if not membership:
        raise HTTPException(status_code=403, detail="Organisation requise.")
    org_id = membership.orgId

    ruleset = await get_or_create_active_ruleset(org_id)

    for cat, (level, active) in tpl.items():
        existing = await prisma.rule.find_first(where={"category": cat, "ruleSetId": ruleset.id})
        if existing:
            await prisma.rule.update(where={"id": existing.id}, data={"level": level, "isActive": active})
        else:
            await prisma.rule.create(data={"category": cat, "level": level, "isActive": active, "orgId": org_id, "ruleSetId": ruleset.id})

    # Increment version & publish event
    new_version = ruleset.version + 1
    await prisma.maskingruleset.update(where={"id": ruleset.id}, data={"version": new_version})
    await event_bus.publish("rule_set.updated", {"organizationId": org_id, "version": new_version})

    return {"status": "success", "template": template}


# ─── CUSTOM REGEX RULES ─────────────────────────────────────────

@router.post("/rules/custom")
async def create_custom_rule(request: CustomRuleRequest, user=Depends(get_current_user)):
    """Create a custom regex-based masking rule for the org's active ruleset."""
    membership = await prisma.membership.find_first(where={"userId": user.id})
    if not membership or membership.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Seuls les admins/managers peuvent créer des règles custom.")

    # Validate the regex
    if len(request.pattern) > 200:
        raise HTTPException(status_code=400, detail="Le motif ne doit pas dépasser 200 caractères.")
    
    # Check for unanchored/infinite loops or nested repetition that cause ReDoS
    if re.search(r'\([^)]*[*+?]\)[*+?]', request.pattern):
        raise HTTPException(status_code=400, detail="Les quantificateurs imbriqués (ex: (a+)+) ne sont pas autorisés pour prévenir les attaques DoS.")
    
    if request.pattern.strip() in (".*", ".+", ".*?", ".+?"):
        raise HTTPException(status_code=400, detail="Le motif ne peut pas être un simple joker générique.")

    try:
        re.compile(request.pattern)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Expression régulière invalide : {str(e)}")

    org_id = membership.orgId
    ruleset = await get_or_create_active_ruleset(org_id)

    # Limit of 20 custom rules per org
    custom_rules_count = await prisma.rule.count(
        where={
            "orgId": org_id,
            "category": "custom",
            "ruleSetId": ruleset.id
        }
    )
    if custom_rules_count >= 20:
        raise HTTPException(status_code=400, detail="Limite de 20 règles personnalisées par organisation atteinte.")

    rule = await prisma.rule.create(data={
        "category": "custom",
        "isActive": True,
        "level": request.level,
        "pattern": request.pattern,
        "format": request.format or "[CUSTOM_{n}]",
        "orgId": org_id,
        "ruleSetId": ruleset.id,
    })

    # Increment version & publish event
    new_version = ruleset.version + 1
    await prisma.maskingruleset.update(where={"id": ruleset.id}, data={"version": new_version})
    await event_bus.publish("rule_set.updated", {"organizationId": org_id, "version": new_version})

    await prisma.auditlog.create(data={
        "action": "rule.custom.create",
        "details": f"Règle regex ajoutée : {request.pattern} [RuleSet v{new_version}]",
        "userId": user.id,
        "orgId": org_id,
    })

    return {
        "id": rule.id,
        "category": rule.category,
        "pattern": rule.pattern,
        "format": rule.format,
        "isActive": rule.isActive,
    }

@router.delete("/rules/custom/{rule_id}")
async def delete_custom_rule(rule_id: str, user=Depends(get_current_user)):
    """Delete a custom regex rule. Only admin/manager."""
    membership = await prisma.membership.find_first(where={"userId": user.id})
    if not membership or membership.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Seuls les admins/managers peuvent supprimer des règles custom.")

    rule = await prisma.rule.find_unique(where={"id": rule_id})
    if not rule or rule.category != "custom":
        raise HTTPException(status_code=404, detail="Règle custom non trouvée.")

    # Isolation check
    if rule.orgId != membership.orgId:
        raise HTTPException(status_code=403, detail="Cette règle n'appartient pas à votre organisation.")

    await prisma.rule.delete(where={"id": rule_id})

    # Increment version & publish event
    ruleset = await prisma.maskingruleset.find_unique(where={"id": rule.ruleSetId})
    if ruleset:
        new_version = ruleset.version + 1
        await prisma.maskingruleset.update(where={"id": ruleset.id}, data={"version": new_version})
        await event_bus.publish("rule_set.updated", {"organizationId": membership.orgId, "version": new_version})

    await prisma.auditlog.create(data={
        "action": "rule.custom.delete",
        "details": f"Règle regex supprimée : {rule.pattern}",
        "userId": user.id,
        "orgId": membership.orgId,
    })

    return {"status": "success"}


# ─── ROTATION ───────────────────────────────────────────────────

@router.post("/rules/rotate")
async def rotate_ruleset(user=Depends(get_current_user)):
    """
    Rotate the MaskingRuleSet for the user's organization using RuleEngine.
    """
    membership = await prisma.membership.find_first(where={"userId": user.id})
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Seuls les administrateurs peuvent effectuer une rotation des clés.")

    org_id = membership.orgId
    
    # Delegate completely to RuleEngine
    new_ruleset = await RuleEngine.rotate_rule_set(org_id)
    
    # Fetch active count of conversations
    active_convs = await prisma.conversation.find_many(
        where={"orgId": org_id, "status": "active", "ruleSetId": new_ruleset.id}
    )

    return {
        "status": "success",
        "old_version": new_ruleset.version - 1,
        "new_version": new_ruleset.version,
        "conversations_migrated": len(active_convs),
    }


# ─── HISTORY ────────────────────────────────────────────────────

@router.get("/rules/history")
async def get_ruleset_history(user=Depends(get_current_user)):
    """Return the version history of MaskingRuleSets for the user's org."""
    membership = await prisma.membership.find_first(where={"userId": user.id})
    if not membership:
        return []

    org_id = membership.orgId
    rulesets = await prisma.maskingruleset.find_many(
        where={"orgId": org_id},
        order={"version": "desc"},
        include={"rules": True}
    )

    return [
        {
            "id": rs.id,
            "version": rs.version,
            "status": rs.status,
            "seed_masked": mask_seed_for_display(rs.seed),
            "rules_count": len(rs.rules) if rs.rules else 0,
            "custom_rules_count": len([r for r in (rs.rules or []) if r.category == "custom"]),
            "createdAt": rs.createdAt.isoformat(),
            "updatedAt": rs.updatedAt.isoformat(),
        }
        for rs in rulesets
    ]


# ─── LIVE PREVIEW ───────────────────────────────────────────────

class PreviewRequest(BaseModel):
    text: str

@router.post("/rules/preview")
async def preview_masking(request: PreviewRequest, user=Depends(get_current_user)):
    """
    Apply the org's current active rules to a sample text and return
    the masked result in real-time. No data is persisted.
    """
    membership = await prisma.membership.find_first(where={"userId": user.id})
    org_id = membership.orgId if membership else None

    active_rules = {"names": True, "contact": True, "finance": True, "dates": True, "documents": True}
    custom_rules = []

    if org_id:
        ruleset = await get_or_create_active_ruleset(org_id)
        for r in (ruleset.rules or []):
            if r.category == "custom" and r.pattern:
                custom_rules.append(r)
            else:
                active_rules[r.category] = r.isActive

    masked = request.text
    mapping = {}

    if active_rules.get("contact", True):
        for m in re.finditer(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', masked):
            o = m.group(0)
            t = f"[EMAIL_{len(mapping)+1}]"
            masked = masked.replace(o, t, 1)
            mapping[o] = t
        for m in re.finditer(r'\+?\d{1,3}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{3}[-.\s]?\d{4}', masked):
            o = m.group(0)
            t = f"[PHONE_{len(mapping)+1}]"
            masked = masked.replace(o, t, 1)
            mapping[o] = t

    if active_rules.get("finance", True):
        for m in re.finditer(r'\b\d+(?:[.,]\d+)?\s*(?:€|\$|FCFA|XOF|XAF)\b', masked):
            o = m.group(0)
            t = f"[MONEY_{len(mapping)+1}]"
            masked = masked.replace(o, t, 1)
            mapping[o] = t

    if active_rules.get("names", True):
        for m in re.finditer(r'\b(?:Jean|Dupont|Alice|Bob|Charlie|Martin|Thomas|Moussa|Diop|Koné)\b', masked):
            o = m.group(0)
            t = f"[NAME_{len(mapping)+1}]"
            masked = masked.replace(o, t, 1)
            mapping[o] = t

    if active_rules.get("dates", True):
        for m in re.finditer(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b', masked):
            o = m.group(0)
            t = f"[DATE_{len(mapping)+1}]"
            masked = masked.replace(o, t, 1)
            mapping[o] = t

    if active_rules.get("documents", True):
        for m in re.finditer(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', masked):
            o = m.group(0)
            t = f"[CARD_{len(mapping)+1}]"
            masked = masked.replace(o, t, 1)
            mapping[o] = t

    # Apply custom regex rules
    for cr in custom_rules:
        if not cr.isActive or not cr.pattern:
            continue
        try:
            counter = 1
            for m in re.finditer(cr.pattern, masked):
                o = m.group(0)
                alias_format = cr.format or f"[CUSTOM_{counter}]"
                t = alias_format.replace("{n}", str(counter))
                masked = masked.replace(o, t, 1)
                mapping[o] = t
                counter += 1
        except re.error:
            pass

    return {
        "original": request.text,
        "masked": masked,
        "entities_found": len(mapping),
        "mapping": mapping,
    }


# ─── ADMIN DEBUG & REGENERATION ────────────────────────────────

@router.get("/admin/organizations/{org_id}/masking-rules/debug")
async def debug_masking_rules(org_id: str, user=Depends(get_current_user)):
    """Return the cached state vs the database state for debugging."""
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")

    # 1. Fetch from Cache
    cached_rules = rule_cache.get(org_id)

    # 2. Fetch from Database
    active_ruleset = await prisma.maskingruleset.find_first(
        where={"orgId": org_id, "status": "active"},
        include={"rules": True}
    )

    return {
        "organizationId": org_id,
        "cache": {
            "has_cache": cached_rules is not None,
            "version": cached_rules.get("version") if cached_rules else None,
            "rules_count": len(cached_rules.get("rules", [])) if cached_rules else 0,
            "rules": cached_rules.get("rules") if cached_rules else []
        },
        "database": {
            "has_ruleset": active_ruleset is not None,
            "ruleset_id": active_ruleset.id if active_ruleset else None,
            "version": active_ruleset.version if active_ruleset else None,
            "status": active_ruleset.status if active_ruleset else None,
            "rules_count": len(active_ruleset.rules) if active_ruleset and active_ruleset.rules else 0,
            "seed_masked": mask_seed_for_display(active_ruleset.seed) if active_ruleset else None
        }
    }


@router.post("/admin/organizations/{org_id}/masking-rules/regenerate")
async def regenerate_masking_rules(org_id: str, user=Depends(get_current_user)):
    """Force rule set generation and rebuild cache."""
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")

    # Generate new rule set
    ruleset = await RuleEngine.generate_rule_set(org_id)

    return {
        "status": "success",
        "message": f"RuleSet v{ruleset.version} généré avec succès. Cache mis à jour.",
        "ruleset_id": ruleset.id,
        "version": ruleset.version
    }

