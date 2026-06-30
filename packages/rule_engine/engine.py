import asyncio
from database import prisma
from services.chiffrement import generate_seed, encrypt_seed, decrypt_seed
from packages.rule_cache import rule_cache
from packages.events import event_bus

class RuleEngine:
    @staticmethod
    async def generate_rule_set(org_id: str, template: str = "default"):
        """Génère un nouveau jeu de règles avec seed chiffré."""
        print(f"[RuleEngine] Generating rule set for org: {org_id} using template: {template}")
        seed = generate_seed()
        encrypted_seed = encrypt_seed(seed)
        
        # Check active version
        latest = await prisma.maskingruleset.find_first(
            where={"orgId": org_id},
            order={"version": "desc"}
        )
        version = (latest.version + 1) if latest else 1

        # Archive previous active rule sets
        if latest:
            await prisma.maskingruleset.update_many(
                where={"orgId": org_id, "status": "active"},
                data={"status": "archived"}
            )

        ruleset = await prisma.maskingruleset.create(data={
            "orgId": org_id,
            "seed": encrypted_seed,
            "status": "active",
            "version": version
        })

        templates = {
            "default": {"names": ("low", True), "contact": ("low", True), "finance": ("low", True), "dates": ("low", True), "documents": ("low", True)},
            "bank": {"names": ("high", True), "contact": ("high", True), "finance": ("high", True), "dates": ("medium", True), "documents": ("high", True)},
            "health": {"names": ("high", True), "contact": ("high", True), "finance": ("low", False), "dates": ("high", True), "documents": ("high", True)},
            "ecommerce": {"names": ("medium", True), "contact": ("high", True), "finance": ("medium", True), "dates": ("low", False), "documents": ("medium", True)},
        }
        tpl = templates.get(template, templates["default"])

        created_rules = []
        for cat, (level, active) in tpl.items():
            r = await prisma.rule.create(data={
                "category": cat,
                "isActive": active,
                "level": level,
                "orgId": org_id,
                "ruleSetId": ruleset.id
            })
            created_rules.append({
                "category": r.category,
                "isActive": r.isActive,
                "level": r.level,
                "pattern": r.pattern,
                "format": r.format
            })

        # Update cache
        rule_cache.set(org_id, version, created_rules)

        # Publish event
        await event_bus.publish("rule_set.created", {
            "organizationId": org_id,
            "version": version
        })

        return ruleset

    @staticmethod
    async def rotate_rule_set(org_id: str):
        """Effectue la rotation du seed de masquage de l'organisation."""
        print(f"[RuleEngine] Rotating rule set for org: {org_id}")
        current = await prisma.maskingruleset.find_first(
            where={"orgId": org_id, "status": "active"},
            include={"rules": True}
        )
        if not current:
            # Fallback to create one
            return await RuleEngine.generate_rule_set(org_id)

        # Create new rule set
        seed = generate_seed()
        encrypted_seed = encrypt_seed(seed)
        new_version = current.version + 1

        # Archive old
        await prisma.maskingruleset.update(
            where={"id": current.id},
            data={"status": "archived"}
        )

        new_ruleset = await prisma.maskingruleset.create(data={
            "orgId": org_id,
            "seed": encrypted_seed,
            "status": "active",
            "version": new_version
        })

        # Copy existing rules to the new ruleset
        copied_rules = []
        for r in (current.rules or []):
            copied = await prisma.rule.create(data={
                "category": r.category,
                "isActive": r.isActive,
                "level": r.level,
                "pattern": r.pattern,
                "format": r.format,
                "orgId": org_id,
                "ruleSetId": new_ruleset.id
            })
            copied_rules.append({
                "category": copied.category,
                "isActive": copied.isActive,
                "level": copied.level,
                "pattern": copied.pattern,
                "format": copied.format
            })

        # Update active conversations to use the new ruleset
        active_convs = await prisma.conversation.find_many(
            where={"orgId": org_id, "status": "active", "ruleSetId": current.id}
        )
        for conv in active_convs:
            await prisma.conversation.update(
                where={"id": conv.id},
                data={"ruleSetId": new_ruleset.id}
            )

        # Update cache
        rule_cache.set(org_id, new_version, copied_rules)

        # Publish event
        await event_bus.publish("rule_set.updated", {
            "organizationId": org_id,
            "version": new_version
        })

        return new_ruleset
