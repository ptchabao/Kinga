import hmac
import hashlib
import base64
import time
import secrets
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from database import prisma
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from packages.auth.rbac import create_default_org_roles_and_admin

router = APIRouter()
SECRET_KEY = b"kinga_super_secret_ledger_key_2026"

# ─── In-memory JTI blacklist (fast path, synced with DB) ────────
_revoked_jtis: set = set()


class TokenHelper:
    @staticmethod
    def generate_token(user_id: str, expires_in: int = 86400) -> str:
        jti = secrets.token_urlsafe(16)
        expiry = str(int(time.time()) + expires_in)
        payload = f"{user_id}:{expiry}:{jti}".encode()
        signature = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
        token_bytes = f"{user_id}:{expiry}:{jti}:{signature}".encode()
        return base64.urlsafe_b64encode(token_bytes).decode()

    @staticmethod
    def verify_token(token: str) -> str:
        try:
            token_bytes = base64.urlsafe_b64decode(token.encode())
            parts = token_bytes.decode().split(":")
            # Support both legacy 3-part and new 4-part tokens
            if len(parts) == 3:
                # Legacy format: user_id:expiry:signature (no jti)
                user_id, expiry, signature = parts
                if int(expiry) < time.time():
                    return None
                payload = f"{user_id}:{expiry}".encode()
                expected_signature = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
                if hmac.compare_digest(signature, expected_signature):
                    return user_id
            elif len(parts) == 4:
                # New format: user_id:expiry:jti:signature
                user_id, expiry, jti, signature = parts
                if int(expiry) < time.time():
                    return None
                # Check revocation (fast path: in-memory set)
                if jti in _revoked_jtis:
                    return None
                payload = f"{user_id}:{expiry}:{jti}".encode()
                expected_signature = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
                if hmac.compare_digest(signature, expected_signature):
                    return user_id
            return None
        except Exception:
            return None

    @staticmethod
    def extract_jti(token: str) -> str:
        """Extract the JTI from a token string. Returns None for legacy tokens."""
        try:
            token_bytes = base64.urlsafe_b64decode(token.encode())
            parts = token_bytes.decode().split(":")
            if len(parts) == 4:
                return parts[2]
        except Exception:
            pass
        return None

    @staticmethod
    def extract_expiry(token: str) -> int:
        """Extract the expiry timestamp from a token string."""
        try:
            token_bytes = base64.urlsafe_b64decode(token.encode())
            parts = token_bytes.decode().split(":")
            if len(parts) >= 3:
                return int(parts[1])
        except Exception:
            pass
        return 0

class HashHelper:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        )
        return f"{salt}:{key.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            salt, key_hex = hashed.split(":")
            expected_key = hashlib.pbkdf2_hmac(
                'sha256', 
                password.encode('utf-8'), 
                salt.encode('utf-8'), 
                100000
            )
            return secrets.compare_digest(expected_key.hex(), key_hex)
        except Exception:
            return False

# Dependency to get current user from Auth Header
async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Non autorisé. Token manquant.")
    token = authorization.split(" ")[1]
    user_id = TokenHelper.verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expirée ou invalide.")
    
    # Check DB-level revocation for new tokens (async, covers multi-instance deployments)
    jti = TokenHelper.extract_jti(token)
    if jti:
        try:
            revoked = await prisma.revokedtoken.find_unique(where={"jti": jti})
            if revoked:
                _revoked_jtis.add(jti)  # Sync to in-memory cache
                raise HTTPException(status_code=401, detail="Session révoquée.")
        except HTTPException:
            raise
        except Exception:
            pass  # DB unavailable — rely on in-memory cache

    user = await prisma.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé.")
    return user

class AuthRequest(BaseModel):
    email: str
    password: str
    name: str = None

class ProfileUpdateRequest(BaseModel):
    name: str = None
    email: str = None

@router.post("/auth/register")
async def register(request: AuthRequest):
    # Check if user exists
    existing = await prisma.user.find_unique(where={"email": request.email})
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est déjà enregistré.")
    
    hashed = HashHelper.hash_password(request.password)
    try:
        user = await prisma.user.create(
            data={
                "email": request.email,
                "passwordHash": hashed,
                "name": request.name or request.email.split("@")[0].capitalize()
            }
        )
        
        # Auto-create default organization
        org_slug = f"org-de-{user.id[:8]}"
        org = await prisma.organization.create(
            data={
                "name": f"Org de {user.name}",
                "slug": org_slug,
                "plan": "free",
                "tokenLimit": 10000,
                "tokenUsed": 0
            }
        )
        
        # Add membership as Admin
        await prisma.membership.create(
            data={
                "userId": user.id,
                "orgId": org.id,
                "role": "admin"
            }
        )
        
        # Auto-create RBAC roles and admin assignment
        await create_default_org_roles_and_admin(org.id, user.id)
        
        # Log audit
        await prisma.auditlog.create(
            data={
                "action": "login",
                "details": f"Nouvel utilisateur enregistré : {user.email}",
                "userId": user.id,
                "orgId": org.id
            }
        )
        
        token = TokenHelper.generate_token(user.id)
        return {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "plan": org.plan,
                "tokenLimit": org.tokenLimit,
                "tokenUsed": org.tokenUsed,
                "role": "admin",
                "orgId": org.id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/login")
async def login(request: AuthRequest):
    user = await prisma.user.find_unique(where={"email": request.email})
    if not user or not HashHelper.verify_password(request.password, user.passwordHash):
        raise HTTPException(status_code=400, detail="Identifiants invalides.")
    
    # Get active organization membership
    membership = await prisma.membership.find_first(
        where={"userId": user.id},
        include={"org": True}
    )
    
    # Fallback to create one if somehow missing
    if not membership:
        org_slug = f"org-de-{user.id[:8]}"
        org = await prisma.organization.create(
            data={
                "name": f"Org de {user.name}",
                "slug": org_slug,
                "plan": "free",
                "tokenLimit": 10000,
                "tokenUsed": 0
            }
        )
        membership = await prisma.membership.create(
            data={
                "userId": user.id,
                "orgId": org.id,
                "role": "admin"
            }
        )
        membership.org = org

    # Log audit
    await prisma.auditlog.create(
        data={
            "action": "login",
            "details": f"Utilisateur connecté : {user.email}",
            "userId": user.id,
            "orgId": membership.orgId
        }
    )

    token = TokenHelper.generate_token(user.id)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "plan": membership.org.plan,
            "tokenLimit": membership.org.tokenLimit,
            "tokenUsed": membership.org.tokenUsed,
            "role": membership.role,
            "orgId": membership.orgId
        }
    }

@router.post("/auth/logout")
async def logout(authorization: str = Header(None)):
    """Révoque le token actuel en ajoutant son JTI à la blacklist."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant.")
    
    token = authorization.split(" ")[1]
    jti = TokenHelper.extract_jti(token)
    
    if not jti:
        # Legacy token — cannot be individually revoked, but we accept the logout
        return {"status": "success", "message": "Déconnexion réussie (token legacy)."}
    
    # Add to in-memory blacklist immediately
    _revoked_jtis.add(jti)
    
    # Persist to DB for multi-instance sync
    try:
        from datetime import datetime
        expiry_ts = TokenHelper.extract_expiry(token)
        expires_at = datetime.fromtimestamp(expiry_ts) if expiry_ts > 0 else datetime.now()
        
        # Extract user_id from token for audit
        user_id = TokenHelper.verify_token(token)
        
        await prisma.revokedtoken.create(
            data={
                "jti": jti,
                "userId": user_id or "unknown",
                "expiresAt": expires_at,
            }
        )
    except Exception as e:
        print(f"[Auth] Warning: Could not persist token revocation to DB: {e}")
    
    return {"status": "success", "message": "Déconnexion réussie. Token révoqué."}

@router.get("/auth/profile")
async def profile(user=Depends(get_current_user)):
    membership = await prisma.membership.find_first(
        where={"userId": user.id},
        include={"org": True}
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Organisation non trouvée.")
        
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "plan": membership.org.plan,
        "tokenLimit": membership.org.tokenLimit,
        "tokenUsed": membership.org.tokenUsed,
        "role": membership.role,
        "orgId": membership.orgId,
        "orgName": membership.org.name
    }

@router.post("/auth/profile")
async def update_profile(request: ProfileUpdateRequest, user=Depends(get_current_user)):
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.email is not None:
        update_data["email"] = request.email

    try:
        updated = await prisma.user.update(
            where={"id": user.id},
            data=update_data
        )
        membership = await prisma.membership.find_first(
            where={"userId": user.id},
            include={"org": True}
        )
        return {
            "id": updated.id,
            "email": updated.email,
            "name": updated.name,
            "plan": membership.org.plan,
            "tokenLimit": membership.org.tokenLimit,
            "tokenUsed": membership.org.tokenUsed,
            "role": membership.role,
            "orgId": membership.orgId,
            "orgName": membership.org.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
