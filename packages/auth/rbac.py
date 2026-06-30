from fastapi import Depends, HTTPException, Path, Header
from database import prisma
import json

async def _get_current_user(authorization: str = Header(None)):
    """Standalone auth check to avoid circular import with routers.auth."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Non autorisé. Token manquant.")
    token = authorization.split(" ")[1]
    from routers.auth import TokenHelper
    user_id = TokenHelper.verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expirée ou invalide.")
    user = await prisma.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé.")
    return user

def require_permission(resource: str, action: str):
    async def dependency(
        user = Depends(_get_current_user),
        org_id: str = Path(...)
    ):
        # 1. Fetch UserOrganizationRole for this user & org
        user_role = await prisma.userorganizationrole.find_first(
            where={"userId": user.id, "organizationId": org_id},
            include={"role": True}
        )
        
        # If user has a UserOrganizationRole with role matching ADMIN, grant access
        if user_role and user_role.role and user_role.role.name.upper() == "ADMIN":
            return user

        # 2. Check if we have specific permissions list
        permissions = []
        if user_role and user_role.role:
            try:
                permissions = json.loads(user_role.role.permissions)
            except Exception:
                permissions = []
        else:
            # Fallback to check Membership role mapping
            membership = await prisma.membership.find_first(
                where={"userId": user.id, "orgId": org_id}
            )
            if not membership:
                raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette organisation.")
            
            role_name = membership.role.upper()
            if role_name == "ADMIN":
                return user
            
            # Map simple membership role to permissions
            if role_name == "MANAGER":
                permissions = [
                    "CONVERSATION:READ", "CONVERSATION:WRITE",
                    "PROFILE:READ", "PROFILE:WRITE",
                    "MEMBER:READ", "MEMBER:WRITE",
                    "MASKING_RULES:READ",
                    "ANALYTICS:READ"
                ]
            else:
                permissions = [
                    "CONVERSATION:READ", "CONVERSATION:WRITE",
                    "PROFILE:READ", "PROFILE:WRITE"
                ]

        required = f"{resource.upper()}:{action.upper()}"
        if required in permissions:
            return user
            
        raise HTTPException(
            status_code=403,
            detail=f"Permission insuffisante : {required} requise."
        )
    return dependency

async def create_default_org_roles_and_admin(org_id: str, user_id: str):
    """Crée les rôles par défaut pour l'organisation et affecte le créateur comme ADMIN."""
    try:
        # 1. Create ADMIN role
        admin_perms = [
            "ORGANIZATION:READ", "ORGANIZATION:WRITE",
            "MEMBER:READ", "MEMBER:WRITE", "MEMBER:DELETE",
            "MASKING_RULES:READ", "MASKING_RULES:WRITE",
            "BILLING:READ", "BILLING:WRITE",
            "AUDIT:READ",
            "SECURITY:WRITE"
        ]
        admin_role = await prisma.role.create(data={
            "name": "ADMIN",
            "organizationId": org_id,
            "permissions": json.dumps(admin_perms)
        })

        # 2. Create MANAGER role
        manager_perms = [
            "CONVERSATION:READ", "CONVERSATION:WRITE",
            "PROFILE:READ", "PROFILE:WRITE",
            "MEMBER:READ", "MEMBER:WRITE",
            "MASKING_RULES:READ",
            "ANALYTICS:READ"
        ]
        await prisma.role.create(data={
            "name": "MANAGER",
            "organizationId": org_id,
            "permissions": json.dumps(manager_perms)
        })

        # 3. Create MEMBER role
        member_perms = [
            "CONVERSATION:READ", "CONVERSATION:WRITE",
            "PROFILE:READ", "PROFILE:WRITE"
        ]
        await prisma.role.create(data={
            "name": "MEMBER",
            "organizationId": org_id,
            "permissions": json.dumps(member_perms)
        })

        # 4. Associate user with ADMIN role
        await prisma.userorganizationrole.create(data={
            "userId": user_id,
            "organizationId": org_id,
            "roleId": admin_role.id
        })
        print(f"[RBAC] Default roles & ADMIN association created for org {org_id} and user {user_id}")
    except Exception as e:
        print(f"[RBAC] Error creating default roles: {e}")
