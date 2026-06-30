from fastapi import APIRouter, Depends
from database import prisma
from routers.auth import get_current_user

router = APIRouter()

@router.get("/audit")
async def get_audit_logs(user=Depends(get_current_user), action: str = None, limit: int = 50):
    membership = await prisma.membership.find_first(where={"userId": user.id})
    
    where = {}
    if membership:
        where["orgId"] = membership.orgId
        # Only admin/manager can see org logs
        if membership.role == "member":
            where["userId"] = user.id
    else:
        where["userId"] = user.id
    
    if action:
        where["action"] = action

    logs = await prisma.auditlog.find_many(
        where=where,
        include={"user": True},
        order={"createdAt": "desc"},
        take=limit
    )
    return [
        {
            "id": l.id,
            "action": l.action,
            "details": l.details,
            "ip": l.ip,
            "userName": l.user.name if l.user else "Système",
            "userEmail": l.user.email if l.user else None,
            "createdAt": l.createdAt.isoformat()
        }
        for l in logs
    ]
