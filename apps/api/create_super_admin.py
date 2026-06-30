"""Script pour créer un compte Super Admin Safiri AI."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import prisma
from routers.auth import HashHelper
import json

ADMIN_EMAIL = "admin@kinga.ai"
ADMIN_PASSWORD = "KingaAdmin2026!"
ADMIN_NAME = "Super Admin"
ORG_NAME = "Kinga HQ"

async def main():
    await prisma.connect()
    
    # 1. Check if user already exists
    existing = await prisma.user.find_unique(where={"email": ADMIN_EMAIL})
    if existing:
        print(f"⚠️  L'utilisateur {ADMIN_EMAIL} existe déjà (id: {existing.id})")
        print(f"   Mot de passe inchangé. Utilisez les credentials existants.")
        await prisma.disconnect()
        return

    # 2. Create user
    hashed = HashHelper.hash_password(ADMIN_PASSWORD)
    user = await prisma.user.create(data={
        "email": ADMIN_EMAIL,
        "passwordHash": hashed,
        "name": ADMIN_NAME,
    })
    print(f"✅ Utilisateur créé : {user.id}")

    # 3. Create organization
    org = await prisma.organization.create(data={
        "name": ORG_NAME,
        "slug": "kinga-hq",
        "plan": "enterprise",
        "tokenLimit": 1000000,
        "tokenUsed": 0,
    })
    print(f"✅ Organisation créée : {org.id} ({org.name})")

    # 4. Create membership (admin)
    await prisma.membership.create(data={
        "userId": user.id,
        "orgId": org.id,
        "role": "admin",
    })
    print(f"✅ Membership admin créé")

    # 5. Create RBAC roles
    admin_perms = [
        "ORGANIZATION:READ", "ORGANIZATION:WRITE",
        "MEMBER:READ", "MEMBER:WRITE", "MEMBER:DELETE",
        "MASKING_RULES:READ", "MASKING_RULES:WRITE",
        "BILLING:READ", "BILLING:WRITE",
        "AUDIT:READ", "SECURITY:WRITE",
    ]
    admin_role = await prisma.role.create(data={
        "name": "ADMIN",
        "organizationId": org.id,
        "permissions": json.dumps(admin_perms),
    })

    manager_perms = [
        "CONVERSATION:READ", "CONVERSATION:WRITE",
        "PROFILE:READ", "PROFILE:WRITE",
        "MEMBER:READ", "MEMBER:WRITE",
        "MASKING_RULES:READ", "ANALYTICS:READ",
    ]
    await prisma.role.create(data={
        "name": "MANAGER",
        "organizationId": org.id,
        "permissions": json.dumps(manager_perms),
    })

    member_perms = ["CONVERSATION:READ", "CONVERSATION:WRITE", "PROFILE:READ", "PROFILE:WRITE"]
    await prisma.role.create(data={
        "name": "MEMBER",
        "organizationId": org.id,
        "permissions": json.dumps(member_perms),
    })
    print(f"✅ Rôles RBAC créés (ADMIN, MANAGER, MEMBER)")

    # 6. Associate user with ADMIN role
    await prisma.userorganizationrole.create(data={
        "userId": user.id,
        "organizationId": org.id,
        "roleId": admin_role.id,
    })
    print(f"✅ UserOrganizationRole ADMIN assigné")

    # 7. Audit log
    await prisma.auditlog.create(data={
        "action": "SUPER_ADMIN_CREATED",
        "details": f"Compte super admin créé : {ADMIN_EMAIL}",
        "userId": user.id,
        "orgId": org.id,
    })

    print("\n" + "=" * 50)
    print("🔐 CREDENTIALS SUPER ADMIN")
    print("=" * 50)
    print(f"   Email    : {ADMIN_EMAIL}")
    print(f"   Password : {ADMIN_PASSWORD}")
    print(f"   Org      : {ORG_NAME}")
    print(f"   Plan     : enterprise")
    print(f"   Rôle     : ADMIN (toutes permissions)")
    print("=" * 50)
    print(f"\n🌐 Connectez-vous sur :")
    print(f"   App user  : http://localhost:3000/login")
    print(f"   App admin : http://localhost:3001/login")

    await prisma.disconnect()

asyncio.run(main())
