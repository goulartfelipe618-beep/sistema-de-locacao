"""Endpoints de health check (liveness e readiness)."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app import __version__
from app.core.cache import check_redis
from app.core.config import settings
from app.core.database import check_database

router = APIRouter(tags=["Infraestrutura"])


class HealthStatus(BaseModel):
    """Resposta do health check."""

    status: str
    version: str
    environment: str
    checks: dict[str, bool] = {}


@router.get("/health", response_model=HealthStatus)
async def liveness() -> HealthStatus:
    """Liveness probe: indica que o processo está no ar (não toca dependências)."""
    return HealthStatus(
        status="ok",
        version=__version__,
        environment=settings.environment,
    )


@router.get("/health/ready", response_model=HealthStatus)
async def readiness(response: Response) -> HealthStatus:
    """Readiness probe: verifica conectividade com banco e cache."""
    db_ok = await check_database()
    redis_ok = await check_redis()
    all_ok = db_ok and redis_ok
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthStatus(
        status="ok" if all_ok else "degraded",
        version=__version__,
        environment=settings.environment,
        checks={"database": db_ok, "redis": redis_ok},
    )
