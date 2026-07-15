"""Tarefas Celery do módulo Comercial / CRM (§7).

Jobs periódicos:
    * Expirar propostas com validade vencida (§7.2).
    * Expirar pontos de fidelidade além do prazo de validade (§7.5).
    * Alertar oportunidades paradas no funil (§7.1).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.comercial.service import (
    FidelidadeService,
    FunilService,
    PropostaService,
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


async def _expirar_propostas_all() -> dict:
    total = 0
    tenants = 0
    for tenant_id in await _tenant_ids():
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            total += await PropostaService(uow.session).expirar_vencidas()
        tenants += 1
    logger.info("CRM propostas expiradas: tenants=%s propostas=%s", tenants, total)
    return {"tenants": tenants, "propostas": total}


async def _expirar_pontos_all() -> dict:
    total = 0
    tenants = 0
    for tenant_id in await _tenant_ids():
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            total += await FidelidadeService(uow.session).expirar_pontos()
        tenants += 1
    logger.info("CRM pontos expirados: tenants=%s pontos=%s", tenants, total)
    return {"tenants": tenants, "pontos": total}


async def _alertar_funil_all(dias: int = 7) -> dict:
    total = 0
    tenants = 0
    for tenant_id in await _tenant_ids():
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            paradas = await FunilService(uow.session).list_paradas(dias=dias)
            total += len(paradas)
        tenants += 1
    logger.info("CRM funil paradas: tenants=%s oportunidades=%s", tenants, total)
    return {"tenants": tenants, "paradas": total}


@celery_app.task(name="comercial.expirar_propostas", queue="default")
def expirar_propostas() -> dict:
    """Job §7.2: expira propostas enviadas/visualizadas com validade vencida."""
    return asyncio.run(_expirar_propostas_all())


@celery_app.task(name="comercial.expirar_pontos_fidelidade", queue="default")
def expirar_pontos_fidelidade() -> dict:
    """Job §7.5: expira pontos de fidelidade além do prazo de validade."""
    return asyncio.run(_expirar_pontos_all())


@celery_app.task(name="comercial.alertar_funil_parado", queue="default")
def alertar_funil_parado() -> dict:
    """Job §7.1: contabiliza oportunidades paradas no funil sem interação."""
    return asyncio.run(_alertar_funil_all())
