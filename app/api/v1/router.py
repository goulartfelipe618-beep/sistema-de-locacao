"""Agregador de rotas da API REST v1.

Cada módulo de negócio contribui com seu ``router``; novas fases apenas
incluem novos módulos aqui.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.cadastros.api import router as cadastros_router
from app.modules.identity.api import router as identity_router
from app.modules.tenants.api import router as tenants_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(identity_router)
api_router.include_router(tenants_router)
api_router.include_router(cadastros_router)
