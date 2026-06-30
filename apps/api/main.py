from fastapi import FastAPI
from contextlib import asynccontextmanager

from routers import chat, payment, auth, keys, orgs, audit
from database import prisma

import sys
import os
import asyncio
import logging
import time
from fastapi import Request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.logging_config import setup_logging
from packages.events import event_bus
from packages.rule_cache import rule_cache

# Setup structured logging
setup_logging()

async def handle_rule_event(event: dict):
    logging.info(f"[BackgroundWorker] Processing rule event: {event}")
    org_id = event.get("organizationId")
    version = event.get("version")
    if not org_id:
        return
    
    try:
        ruleset = await prisma.maskingruleset.find_first(
            where={"orgId": org_id, "version": version},
            include={"rules": True}
        )
        if ruleset:
            rules_list = []
            for r in (ruleset.rules or []):
                rules_list.append({
                    "category": r.category,
                    "isActive": r.isActive,
                    "level": r.level,
                    "pattern": r.pattern,
                    "format": r.format
                })
            rule_cache.set(org_id, version, rules_list)
            logging.info(f"[BackgroundWorker] Successfully updated Redis cache for org {org_id} to v{version}")
    except Exception as e:
        logging.error(f"[BackgroundWorker] Error updating cache for org {org_id}: {e}", exc_info=True)

# Subscribe to events
event_bus.subscribe("rule_set.created", handle_rule_event)
event_bus.subscribe("rule_set.updated", handle_rule_event)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage de l'app : Connexion à Prisma
    try:
        await prisma.connect()
        logging.info("Connecté à la base de données via Prisma")
    except Exception as e:
        logging.error(f"Attention: Impossible de se connecter à la BDD ({e}). L'API continue en mode dégradé (sans sauvegarde).", exc_info=True)
        
    # Start Event Bus background listener loop
    listener_task = asyncio.create_task(event_bus.start_listening())
    
    yield
    
    # Cancel Event Bus listener loop
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

    # Arrêt de l'app : Déconnexion de Prisma
    if prisma.is_connected():
        await prisma.disconnect()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Kinga API",
    description="API Backend pour Kinga avec brouillage réversible, sauvegarde BDD, et paiements simulés.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    logging.info(
        f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {process_time:.2f}ms",
        extra={
            "metrics": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": process_time
            }
        }
    )
    return response

# Inclusion des routeurs
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(payment.router, prefix="/api/payment", tags=["payment"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(keys.router, prefix="/api", tags=["keys"])
app.include_router(orgs.router, prefix="/api", tags=["organizations"])
app.include_router(audit.router, prefix="/api", tags=["audit"])
from routers import admin
app.include_router(admin.router, prefix="/api", tags=["admin"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Kinga API"}
