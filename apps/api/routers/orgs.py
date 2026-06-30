import secrets
import json
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from database import prisma
from routers.auth import get_current_user
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from packages.rule_engine.engine import RuleEngine

router = APIRouter()

class OrgCreateRequest(BaseModel):
    name: str

class InviteRequest(BaseModel):
    email: str
    role: str = "member"

class RoleUpdateRequest(BaseModel):
    role: str

# ─── ORGANIZATION CRUD ──────────────────────────────────────────

@router.post("/orgs")
async def create_org(request: OrgCreateRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    slug = request.name.lower().replace(" ", "-").replace("'", "")[:30]
    # Check unique slug
    existing = await prisma.organization.find_unique(where={"slug": slug})
    if existing:
        slug = f"{slug}-{secrets.token_hex(3)}"
    
    org = await prisma.organization.create(data={
        "name": request.name,
        "slug": slug,
        "plan": "free",
        "tokenLimit": 10000,
        "tokenUsed": 0
    })
    # Auto-add creator as admin
    await prisma.membership.create(data={
        "userId": user.id,
        "orgId": org.id,
        "role": "admin"
    })
    
    # Auto-create RBAC roles and admin assignment
    from packages.auth.rbac import create_default_org_roles_and_admin
    await create_default_org_roles_and_admin(org.id, user.id)
    
    # Trigger background rule set generation
    background_tasks.add_task(RuleEngine.generate_rule_set, org.id)
    
    await prisma.auditlog.create(data={
        "action": "org.create",
        "details": f"Organisation '{request.name}' créée. Génération des règles lancée en arrière-plan.",
        "userId": user.id,
        "orgId": org.id,
    })
    return {"id": org.id, "name": org.name, "slug": org.slug, "plan": org.plan}

@router.get("/orgs")
async def get_my_orgs(user=Depends(get_current_user)):
    memberships = await prisma.membership.find_many(
        where={"userId": user.id},
        include={"org": True}
    )
    return [
        {
            "id": m.org.id,
            "name": m.org.name,
            "slug": m.org.slug,
            "plan": m.org.plan,
            "role": m.role,
            "tokenLimit": m.org.tokenLimit,
            "tokenUsed": m.org.tokenUsed,
        }
        for m in memberships
    ]

@router.get("/orgs/{org_id}")
async def get_org(org_id: str, user=Depends(get_current_user)):
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette organisation.")
    
    org = await prisma.organization.find_unique(where={"id": org_id})
    members = await prisma.membership.find_many(
        where={"orgId": org_id},
        include={"user": True}
    )
    teams = await prisma.team.find_many(where={"orgId": org_id})

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "tokenLimit": org.tokenLimit,
        "tokenUsed": org.tokenUsed,
        "role": membership.role,
        "members": [
            {
                "id": m.user.id,
                "name": m.user.name,
                "email": m.user.email,
                "role": m.role,
                "teamId": m.teamId,
                "joinedAt": m.createdAt.isoformat()
            }
            for m in members
        ],
        "teams": [{"id": t.id, "name": t.name} for t in teams]
    }

# ─── MEMBERS ────────────────────────────────────────────────────

@router.post("/orgs/{org_id}/invite")
async def invite_member(org_id: str, request: InviteRequest, user=Depends(get_current_user)):
    # Check admin or manager
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership or membership.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Seuls les admins et managers peuvent inviter.")

    # Find user by email
    target_user = await prisma.user.find_unique(where={"email": request.email})
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé. Il doit d'abord créer un compte Kinga.")
    
    # Check if already member
    existing = await prisma.membership.find_first(where={"userId": target_user.id, "orgId": org_id})
    if existing:
        raise HTTPException(status_code=400, detail="Cet utilisateur est déjà membre de l'organisation.")
    
    await prisma.membership.create(data={
        "userId": target_user.id,
        "orgId": org_id,
        "role": request.role
    })
    await prisma.auditlog.create(data={
        "action": "member.invite",
        "details": f"Invitation de {request.email} (rôle: {request.role})",
        "userId": user.id,
        "orgId": org_id,
    })
    return {"status": "success", "message": f"{request.email} ajouté comme {request.role}"}

@router.patch("/orgs/{org_id}/members/{member_id}")
async def update_member_role(org_id: str, member_id: str, request: RoleUpdateRequest, user=Depends(get_current_user)):
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent modifier les rôles.")

    target = await prisma.membership.find_first(where={"userId": member_id, "orgId": org_id})
    if not target:
        raise HTTPException(status_code=404, detail="Membre non trouvé.")
    
    await prisma.membership.update(where={"id": target.id}, data={"role": request.role})
    return {"status": "success", "message": f"Rôle mis à jour: {request.role}"}

@router.delete("/orgs/{org_id}/members/{member_id}")
async def remove_member(org_id: str, member_id: str, user=Depends(get_current_user)):
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Seuls les admins peuvent retirer des membres.")
    
    target = await prisma.membership.find_first(where={"userId": member_id, "orgId": org_id})
    if not target:
        raise HTTPException(status_code=404, detail="Membre non trouvé.")
    
    await prisma.membership.delete(where={"id": target.id})
    return {"status": "success"}

# ─── TEAMS ──────────────────────────────────────────────────────

@router.post("/orgs/{org_id}/teams")
async def create_team(org_id: str, name: str, user=Depends(get_current_user)):
    membership = await prisma.membership.find_first(where={"userId": user.id, "orgId": org_id})
    if not membership or membership.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Seuls les admins/managers peuvent créer des équipes.")
    
    team = await prisma.team.create(data={"name": name, "orgId": org_id})
    return {"id": team.id, "name": team.name}

@router.get("/orgs/{org_id}/teams")
async def list_teams(org_id: str, user=Depends(get_current_user)):
    teams = await prisma.team.find_many(
        where={"orgId": org_id},
        include={"members": {"include": {"user": True}}}
    )
    return [
        {
            "id": t.id,
            "name": t.name,
            "members": [
                {"id": m.user.id, "name": m.user.name, "email": m.user.email, "role": m.role}
                for m in t.members
            ]
        }
        for t in teams
    ]

@router.post("/orgs/{org_id}/teams/{team_id}/members")
async def add_team_member(org_id: str, team_id: str, member_id: str, user=Depends(get_current_user)):
    membership = await prisma.membership.find_first(where={"userId": member_id, "orgId": org_id})
    if not membership:
        raise HTTPException(status_code=404, detail="L'utilisateur n'est pas membre de l'organisation.")
    
    await prisma.membership.update(where={"id": membership.id}, data={"teamId": team_id})
    return {"status": "success"}
