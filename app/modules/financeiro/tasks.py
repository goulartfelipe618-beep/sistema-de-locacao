"""Tarefas Celery do módulo Financeiro (§9).

Jobs periódicos:
    * Marcar títulos a receber/pagar vencidos.
    * Expirar cobranças PIX pendentes.
    * Fechar ciclos de faturamento consolidado.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.financeiro.service import (
    ContaPagarService,
    ContaReceberService,
    FaturamentoService,
    PixService,
)
from app.modules.tenants.models import Tenant
from app.shared.enums import TenantStatus
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _tenant_ids() -> list:
    async with UnitOfWork(tenant_id=None) as uow:
        result = await uow.session.execute(
            select(Tenant.id).where(
                Tenant.status == TenantStatus.ACTIVE,
                Tenant.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())


async def _marcar_vencidos_all() -> dict:
    total_cr = 0
    total_cp = 0
    tenants = 0
    for tenant_id in await _tenant_ids():
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            total_cr += await ContaReceberService(uow.session).marcar_vencidos()
            total_cp += await ContaPagarService(uow.session).marcar_vencidos()
        tenants += 1
    logger.info("Financeiro vencidos: tenants=%s cr=%s cp=%s", tenants, total_cr, total_cp)
    return {"tenants": tenants, "receber": total_cr, "pagar": total_cp}


async def _expirar_pix_all() -> dict:
    total = 0
    tenants = 0
    for tenant_id in await _tenant_ids():
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            total += await PixService(uow.session).expirar_vencidas()
        tenants += 1
    logger.info("PIX expiradas: tenants=%s cobrancas=%s", tenants, total)
    return {"tenants": tenants, "expiradas": total}


async def _fechar_faturamento_all() -> dict:
    total = 0
    tenants = 0
    for tenant_id in await _tenant_ids():
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            faturas = await FaturamentoService(uow.session).fechar_ciclos(tenant_id)
            total += len(faturas)
        tenants += 1
    logger.info("Faturamento fechado: tenants=%s faturas=%s", tenants, total)
    return {"tenants": tenants, "faturas": total}


@celery_app.task(name="financeiro.marcar_vencidos", queue="default")
def marcar_vencidos() -> dict:
    """Job §9.2/§9.3: marca títulos a receber/pagar vencidos."""
    return asyncio.run(_marcar_vencidos_all())


@celery_app.task(name="financeiro.expirar_pix", queue="default")
def expirar_pix() -> dict:
    """Job §9.4: expira cobranças PIX aguardando além do prazo."""
    return asyncio.run(_expirar_pix_all())


@celery_app.task(name="financeiro.fechar_faturamento", queue="default")
def fechar_faturamento() -> dict:
    """Job §9.8: consolida faturas nos ciclos com fechamento no dia atual."""
    return asyncio.run(_fechar_faturamento_all())
