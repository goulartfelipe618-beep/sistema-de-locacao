"""Agregador de rotas Web (painel administrativo, HTML).

Cada módulo contribui com seu ``router`` de páginas. Novas fases apenas incluem
novos módulos aqui.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.web import router as audit_router
from app.modules.dashboard.web import router as dashboard_router
from app.modules.identity.web import router as identity_router
from app.modules.tenants.web import router as tenants_router

web_router = APIRouter(include_in_schema=False)

web_router.include_router(dashboard_router)
web_router.include_router(identity_router)
web_router.include_router(tenants_router)
web_router.include_router(audit_router)
