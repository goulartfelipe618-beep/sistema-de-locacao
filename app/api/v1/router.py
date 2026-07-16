"""Agregador de rotas da API REST v1.

Cada módulo de negócio contribui com seu ``router``; novas fases apenas
incluem novos módulos aqui.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.cadastros.api import router as cadastros_router
from app.modules.comercial.api import router as comercial_router
from app.modules.financeiro.api import router as financeiro_router
from app.modules.fiscal.api import router as fiscal_router
from app.modules.automacoes.api import router as automacoes_router
from app.modules.integracoes.api import router as integracoes_router, webhooks_router
from app.modules.integracoes.public_api import public_router
from app.modules.relatorios.api import router as relatorios_router
from app.modules.frota.api import router as frota_router
from app.modules.identity.api import router as identity_router
from app.modules.locacoes.api import router as locacoes_router
from app.modules.manutencao.api import router as manutencao_router
from app.modules.reservas.api import router as reservas_router
from app.modules.tarifario.api import router as tarifario_router
from app.modules.tenants.api import router as tenants_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(identity_router)
api_router.include_router(tenants_router)
api_router.include_router(cadastros_router)
api_router.include_router(frota_router)
api_router.include_router(manutencao_router)
api_router.include_router(tarifario_router)
api_router.include_router(reservas_router)
api_router.include_router(locacoes_router)
api_router.include_router(financeiro_router)
api_router.include_router(comercial_router)
api_router.include_router(fiscal_router)
api_router.include_router(automacoes_router)
api_router.include_router(integracoes_router)
api_router.include_router(webhooks_router)
api_router.include_router(public_router)
api_router.include_router(relatorios_router)
