import secrets
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from routers.auth import get_current_user
from database import prisma

router = APIRouter()

class KeyCreateRequest(BaseModel):
    name: str

@router.get("/keys")
async def list_keys(user=Depends(get_current_user)):
    keys = await prisma.apikey.find_many(
        where={"userId": user.id},
        order={"createdAt": "desc"}
    )
    return [
        {
            "id": k.id,
            "name": k.name,
            "key": f"{k.key[:12]}...{k.key[-4:]}", # Mask key in list
            "created_at": k.createdAt.isoformat()
        }
        for k in keys
    ]

@router.post("/keys")
async def create_key(request: KeyCreateRequest, user=Depends(get_current_user)):
    raw_key = f"kinga_live_{secrets.token_urlsafe(32)}"
    key_entry = await prisma.apikey.create(
        data={
            "name": request.name,
            "key": raw_key,
            "userId": user.id
        }
    )
    return {
        "id": key_entry.id,
        "name": key_entry.name,
        "key": raw_key, # Return raw key only once
        "created_at": key_entry.createdAt.isoformat()
    }

@router.delete("/keys/{key_id}")
async def delete_key(key_id: str, user=Depends(get_current_user)):
    # Verify owner
    key_entry = await prisma.apikey.find_unique(where={"id": key_id})
    if not key_entry or key_entry.userId != user.id:
        return {"status": "error", "message": "Clé non trouvée ou non autorisée."}
        
    await prisma.apikey.delete(where={"id": key_id})
    return {"status": "success", "message": "Clé API révoquée avec succès."}
