"""Agregador de rotas Web (painel administrativo, HTML).

Cada módulo contribui com seu ``router`` de páginas. Novas fases apenas incluem
novos módulos aqui.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.web import router as audit_router
from app.modules.cadastros.web import router as cadastros_router
from app.modules.comercial.web import router as comercial_router
from app.modules.dashboard.web import router as dashboard_router
from app.modules.financeiro.web import router as financeiro_router
from app.modules.fiscal.web import router as fiscal_router
from app.modules.integracoes.web import router as integracoes_router
from app.modules.relatorios.web import router as relatorios_router
from app.modules.frota.web import router as frota_router
from app.modules.identity.web import router as identity_router
from app.modules.locacoes.web import router as locacoes_router
from app.modules.manutencao.web import router as manutencao_router
from app.modules.reservas.web import router as reservas_router
from app.modules.tarifario.web import router as tarifario_router
from app.modules.tenants.web import router as tenants_router

web_router = APIRouter(include_in_schema=False)

web_router.include_router(dashboard_router)
web_router.include_router(identity_router)
web_router.include_router(tenants_router)
web_router.include_router(cadastros_router)
web_router.include_router(frota_router)
web_router.include_router(manutencao_router)
web_router.include_router(tarifario_router)
web_router.include_router(reservas_router)
web_router.include_router(locacoes_router)
web_router.include_router(financeiro_router)
web_router.include_router(comercial_router)
web_router.include_router(fiscal_router)
web_router.include_router(integracoes_router)
web_router.include_router(relatorios_router)
web_router.include_router(audit_router)
