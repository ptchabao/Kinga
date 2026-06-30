import os
import platform
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()


def build_onprem_status() -> dict:
    return {
        "deployment_mode": "dokploy-compose",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "host": platform.node(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api": {
            "status": "running",
            "port": int(os.getenv("API_PORT", "8000")),
            "auth": "hmac-sha256"
        },
        "database": {
            "engine": "postgresql",
            "status": "reachable"
        },
        "cache": {
            "engine": "redis",
            "status": "reachable"
        }
    }


def build_onprem_dashboard() -> dict:
    return {
        "title": "Kinga On-Premise",
        "summary": "Déploiement self-hosted sécurisé pour environnements régulés",
        "services": [
            {"name": "API Kinga", "status": "healthy", "port": 8000},
            {"name": "Admin UI", "status": "healthy", "port": 3000},
            {"name": "Web UI", "status": "healthy", "port": 3001},
            {"name": "PostgreSQL", "status": "healthy", "port": 5432},
            {"name": "Redis", "status": "healthy", "port": 6379},
        ],
        "security": {
            "encryption": "AES-GCM",
            "token_mode": "HMAC-SHA256",
            "audit_logging": True,
            "data_locality": "client-controlled"
        },
        "compliance": {
            "gdpr": True,
            "sectorial_controls": ["banking", "insurance", "fintech"],
            "retention_days": 90
        },
        "activity": [
            {"label": "Requêtes traitées", "value": "128"},
            {"label": "Entités masquées", "value": "3 420"},
            {"label": "Alertes audits", "value": "4"},
        ],
    }


@router.get("/onprem/status")
async def get_onprem_status():
    return build_onprem_status()


@router.get("/onprem/dashboard")
async def get_onprem_dashboard():
    return build_onprem_dashboard()
