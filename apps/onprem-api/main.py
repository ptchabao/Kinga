import os
import sys
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
for candidate in (str(API_ROOT), str(REPO_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from apps.api.main import app as api_app
from apps.api.routers.onprem import router as onprem_router

app = api_app
app.title = "Kinga On-Premise API"
app.version = "1.0.0"
app.include_router(onprem_router, prefix="/api", tags=["onprem"])


class OnPremStatus(BaseModel):
    deployment_mode: str
    region: str
    status: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status", response_model=OnPremStatus)
def status():
    return {
        "deployment_mode": "dokploy-compose",
        "region": "self-hosted",
        "status": "running"
    }
