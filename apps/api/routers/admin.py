import json
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from pydantic import BaseModel
from typing import Optional, List
from database import prisma
from packages.auth.rbac import require_permission
from packages.rule_cache.cache import rule_cache
from packages.events import event_bus

router = APIRouter()

# ─── MODELS ─────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    role: str = "MEMBER"  # MEMBER, MANAGER, ADMIN

class MemberRoleUpdateRequest(BaseModel):
    role: str

class RuleUpdateRequest(BaseModel):
    id: str
    isActive: bool
    level: str = "low"
    pattern: Optional[str] = None
    format: Optional[str] = None

class BillingPlanRequest(BaseModel):
    plan: str  # free | starter | pro | enterprise

class OrgSettingsRequest(BaseModel):
    name: str

# ─── DASHBOARD ──────────────────────────────────────────────────

@router.get("/organizations/{org_id}/dashboard")
async def get_admin_dashboard(
    org_id: str = Path(...),
    user = Depends(require_permission("organization", "read"))
):
    # Members count
    members_count = await prisma.membership.count(where={"orgId": org_id})
    
    # Audit logs count (activity)
    activity_count = await prisma.auditlog.count(where={"orgId": org_id})

    # Org stats
    org = await prisma.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée.")

    # Return structured stats
    return {
        "membersCount": members_count,
        "tokenUsed": org.tokenUsed,
        "tokenLimit": org.tokenLimit,
        "plan": org.plan,
        "activityCount": activity_count,
        "maskingRate": 84.5,  # Simulated rate %
        "securityAlerts": [
            {
                "id": "1",
                "type": "warning",
                "message": "Désactivation temporaire de la règle EMAIL",
                "createdAt": "2026-06-24T10:00:00Z"
            }
        ],
        "chartData": [
            {"date": "24 Juin", "requests": 12, "tokens": 4800},
            {"date": "23 Juin", "requests": 8, "tokens": 3200},
            {"date": "22 Juin", "requests": 15, "tokens": 6000},
            {"date": "21 Juin", "requests": 5, "tokens": 2000},
        ]
    }

# ─── MEMBERS MANAGEMENT ─────────────────────────────────────────

@router.get("/organizations/{org_id}/members")
async def list_members(
    org_id: str = Path(...),
    user = Depends(require_permission("member", "read"))
):
    memberships = await prisma.membership.find_many(
        where={"orgId": org_id},
        include={"user": True}
    )
    
    # Enrich with Role model names
    enriched = []
    for m in memberships:
        user_role = await prisma.userorganizationrole.find_first(
            where={"userId": m.userId, "organizationId": org_id},
            include={"role": True}
        )
        role_name = user_role.role.name if user_role and user_role.role else m.role.upper()
        enriched.append({
            "id": m.id,
            "userId": m.userId,
            "email": m.user.email,
            "name": m.user.name,
            "role": role_name,
            "createdAt": m.createdAt
        })
    return enriched

@router.post("/organizations/{org_id}/members")
async def invite_member(
    request: InviteRequest,
    org_id: str = Path(...),
    admin_user = Depends(require_permission("member", "write"))
):
    email = request.email.lower().strip()
    # 1. Find or create user
    user = await prisma.user.find_unique(where={"email": email})
    if not user:
        # Create user with default dummy password
        from routers.auth import HashHelper
        dummy_pass = HashHelper.hash_password("kinga_welcome_2026")
        user = await prisma.user.create(data={
            "email": email,
            "passwordHash": dummy_pass,
            "name": email.split("@")[0].capitalize()
        })
    
    # 2. Check if already member
    existing = await prisma.membership.find_first(
        where={"userId": user.id, "orgId": org_id}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Cet utilisateur est déjà membre de l'organisation.")

    # 3. Create membership
    await prisma.membership.create(data={
        "userId": user.id,
        "orgId": org_id,
        "role": request.role.lower()
    })

    # 4. Associate with Role
    role = await prisma.role.find_first(
        where={"name": request.role.upper(), "organizationId": org_id}
    )
    if role:
        await prisma.userorganizationrole.create(data={
            "userId": user.id,
            "organizationId": org_id,
            "roleId": role.id
        })

    # Audit
    await prisma.auditlog.create(data={
        "action": "CREATE_MEMBER",
        "details": f"Utilisateur {email} invité avec le rôle {request.role}.",
        "userId": admin_user.id,
        "orgId": org_id
    })

    return {"status": "success", "message": f"Utilisateur {email} invité."}

@router.patch("/organizations/{org_id}/members/{user_id}")
async def update_member_role(
    request: MemberRoleUpdateRequest,
    org_id: str = Path(...),
    user_id: str = Path(...),
    admin_user = Depends(require_permission("member", "write"))
):
    # 1. Check if membership exists
    membership = await prisma.membership.find_first(
        where={"userId": user_id, "orgId": org_id}
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membre non trouvé.")

    # Update simple role
    await prisma.membership.update(
        where={"id": membership.id},
        data={"role": request.role.lower()}
    )

    # 2. Update UserOrganizationRole
    role = await prisma.role.find_first(
        where={"name": request.role.upper(), "organizationId": org_id}
    )
    if role:
        # Delete existing role mapping
        await prisma.userorganizationrole.delete_many(
            where={"userId": user_id, "organizationId": org_id}
        )
        # Create new
        await prisma.userorganizationrole.create(data={
            "userId": user_id,
            "organizationId": org_id,
            "roleId": role.id
        })

    # Audit
    await prisma.auditlog.create(data={
        "action": "UPDATE_MEMBER_ROLE",
        "details": f"Rôle de l'utilisateur {user_id} mis à jour vers {request.role}.",
        "userId": admin_user.id,
        "orgId": org_id
    })

    return {"status": "success"}

@router.delete("/organizations/{org_id}/members/{user_id}")
async def remove_member(
    org_id: str = Path(...),
    user_id: str = Path(...),
    admin_user = Depends(require_permission("member", "delete"))
):
    membership = await prisma.membership.find_first(
        where={"userId": user_id, "orgId": org_id}
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membre non trouvé.")

    await prisma.membership.delete(where={"id": membership.id})
    await prisma.userorganizationrole.delete_many(
        where={"userId": user_id, "organizationId": org_id}
    )

    # Audit
    await prisma.auditlog.create(data={
        "action": "DELETE_MEMBER",
        "details": f"Utilisateur {user_id} retiré de l'organisation.",
        "userId": admin_user.id,
        "orgId": org_id
    })

    return {"status": "success", "message": "Membre retiré avec succès."}

# ─── MASKING RULES ──────────────────────────────────────────────

@router.get("/organizations/{org_id}/masking-rules")
async def get_masking_rules(
    org_id: str = Path(...),
    user = Depends(require_permission("masking_rules", "read"))
):
    ruleset = await prisma.maskingruleset.find_first(
        where={"orgId": org_id, "status": "active"},
        include={"rules": True}
    )
    if not ruleset:
        # Fallback empty structure
        return {"version": 1, "rules": []}

    return {
        "version": ruleset.version,
        "rulesetId": ruleset.id,
        "rules": [
            {
                "id": r.id,
                "category": r.category,
                "isActive": r.isActive,
                "level": r.level,
                "pattern": r.pattern,
                "format": r.format
            } for r in ruleset.rules
        ]
    }

@router.patch("/organizations/{org_id}/masking-rules/{rule_id}")
async def update_masking_rule(
    request: RuleUpdateRequest,
    org_id: str = Path(...),
    rule_id: str = Path(...),
    admin_user = Depends(require_permission("masking_rules", "write"))
):
    # Find existing rule
    rule = await prisma.rule.find_first(
        where={"id": rule_id, "orgId": org_id}
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée.")

    # Update rule fields
    update_data = {
        "isActive": request.isActive,
        "level": request.level,
    }
    if request.pattern is not None:
        update_data["pattern"] = request.pattern
    if request.format is not None:
        update_data["format"] = request.format

    updated = await prisma.rule.update(
        where={"id": rule_id},
        data=update_data
    )

    # Invalidate Cache
    rule_cache.invalidate(org_id)

    # Increment Version on MaskingRuleSet & publish update
    if rule.ruleSetId:
        ruleset = await prisma.maskingruleset.find_unique(where={"id": rule.ruleSetId})
        if ruleset:
            new_version = ruleset.version + 1
            await prisma.maskingruleset.update(
                where={"id": ruleset.id},
                data={"version": new_version}
            )
            # Fetch all rules for the ruleset to update cache
            all_rules = await prisma.rule.find_many(where={"ruleSetId": ruleset.id})
            rules_list = [
                {
                    "category": r.category,
                    "isActive": r.isActive,
                    "level": r.level,
                    "pattern": r.pattern,
                    "format": r.format
                } for r in all_rules
            ]
            rule_cache.set(org_id, new_version, rules_list)
            
            await event_bus.publish("rule_set.updated", {
                "organizationId": org_id,
                "version": new_version
            })

    # Audit log
    await prisma.auditlog.create(data={
        "action": "rule.update",
        "details": f"Règle '{rule.category}' mise à jour (active: {request.isActive}, niveau: {request.level}).",
        "userId": admin_user.id,
        "orgId": org_id
    })

    return updated

# ─── AUDIT LOGS ─────────────────────────────────────────────────

@router.get("/organizations/{org_id}/audit-logs")
async def get_audit_logs(
    org_id: str = Path(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user = Depends(require_permission("audit", "read"))
):
    skip = (page - 1) * limit
    logs = await prisma.auditlog.find_many(
        where={"orgId": org_id},
        order={"createdAt": "desc"},
        skip=skip,
        take=limit,
        include={"user": True}
    )
    total = await prisma.auditlog.count(where={"orgId": org_id})
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "details": log.details,
                "ip": log.ip,
                "createdAt": log.createdAt,
                "userName": log.user.name if log.user else "System"
            } for log in logs
        ]
    }

# ─── BILLING ────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/billing")
async def get_billing_info(
    org_id: str = Path(...),
    user = Depends(require_permission("billing", "read"))
):
    org = await prisma.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée.")

    invoices = await prisma.invoice.find_many(
        where={"orgId": org_id},
        order={"createdAt": "desc"}
    )

    return {
        "plan": org.plan,
        "tokenLimit": org.tokenLimit,
        "tokenUsed": org.tokenUsed,
        "renewalDate": "2026-07-24T12:00:00Z",
        "invoices": [
            {
                "id": inv.id,
                "amount": inv.amount,
                "currency": inv.currency,
                "status": inv.status,
                "period": inv.period,
                "createdAt": inv.createdAt
            } for inv in invoices
        ]
    }

@router.patch("/organizations/{org_id}/billing")
async def update_billing_plan(
    request: BillingPlanRequest,
    org_id: str = Path(...),
    admin_user = Depends(require_permission("billing", "write"))
):
    org = await prisma.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée.")

    limits = {
        "free": 10000,
        "starter": 50000,
        "pro": 200000,
        "enterprise": 1000000
    }
    limit = limits.get(request.plan.lower(), 10000)

    # Update plan
    await prisma.organization.update(
        where={"id": org_id},
        data={"plan": request.plan.lower(), "tokenLimit": limit}
    )

    # Create dummy invoice
    costs = {"free": 0.0, "starter": 29.0, "pro": 149.0, "enterprise": 999.0}
    cost = costs.get(request.plan.lower(), 0.0)
    if cost > 0:
        await prisma.invoice.create(data={
            "amount": cost,
            "currency": "EUR",
            "status": "paid",
            "period": "2026-06",
            "orgId": org_id
        })

    # Audit
    await prisma.auditlog.create(data={
        "action": "UPDATE_BILLING",
        "details": f"Plan d'abonnement mis à jour vers {request.plan} (limite : {limit} tokens).",
        "userId": admin_user.id,
        "orgId": org_id
    })

    return {"status": "success", "plan": request.plan, "tokenLimit": limit}

# ─── SETTINGS ───────────────────────────────────────────────────

@router.get("/organizations/{org_id}/settings")
async def get_org_settings(
    org_id: str = Path(...),
    user = Depends(require_permission("organization", "read"))
):
    org = await prisma.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée.")

    api_keys = await prisma.apikey.find_many(
        where={"userId": user.id} # In simple sqlite demo, fetch keys generated by this admin
    )

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "domain": f"{org.slug}.kinga.ai",
        "logoUrl": None,
        "apiKeys": [
            {
                "id": k.id,
                "name": k.name,
                "key": f"{k.key[:8]}...{k.key[-4:]}",
                "createdAt": k.createdAt
            } for k in api_keys
        ]
    }

@router.patch("/organizations/{org_id}/settings")
async def update_org_settings(
    request: OrgSettingsRequest,
    org_id: str = Path(...),
    admin_user = Depends(require_permission("organization", "write"))
):
    org = await prisma.organization.find_unique(where={"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée.")

    await prisma.organization.update(
        where={"id": org_id},
        data={"name": request.name}
    )

    # Audit
    await prisma.auditlog.create(data={
        "action": "UPDATE_SETTINGS",
        "details": f"Paramètres de l'organisation mis à jour : nom changé en '{request.name}'.",
        "userId": admin_user.id,
        "orgId": org_id
    })

    return {"status": "success", "name": request.name}
