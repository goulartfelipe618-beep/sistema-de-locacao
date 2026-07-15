"""Tarefas Celery do módulo Manutenção (planos preventivos)."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.manutencao.service import PlanoPreventivoService
from app.modules.tenants.models import Tenant
from app.shared.enums import TenantStatus
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _avaliar_todos_tenants() -> dict[str, int]:
    os_geradas = 0
    tenants_processados = 0
    async with UnitOfWork(tenant_id=None) as uow:
        result = await uow.session.execute(
            select(Tenant.id).where(
                Tenant.status == TenantStatus.ACTIVE,
                Tenant.deleted_at.is_(None),
            )
        )
        tenant_ids = list(result.scalars().all())

    for tenant_id in tenant_ids:
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            criadas = await PlanoPreventivoService(uow.session).avaliar_planos_automaticos(
                tenant_id
            )
            os_geradas += len(criadas)
            tenants_processados += 1

    logger.info(
        "Preventivas avaliadas: tenants=%s os_geradas=%s",
        tenants_processados,
        os_geradas,
    )
    return {"tenants": tenants_processados, "os_geradas": os_geradas}


@celery_app.task(name="manutencao.avaliar_preventivas", queue="maintenance")
def avaliar_preventivas() -> dict[str, int]:
    """Job diário (§4.2): gera OS preventiva ao atingir 100% do gatilho km/tempo."""
    return asyncio.run(_avaliar_todos_tenants())
