"""Tarefas Celery do módulo Integrações (fila ``integrations``)."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.integracoes.service import TelemetriaIntegracaoService
from app.modules.tenants.models import Tenant
from app.shared.enums import TenantStatus
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _sync_telemetria_tenant(tenant_id: uuid.UUID) -> dict:
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        return await TelemetriaIntegracaoService(uow.session).sincronizar(tenant_id)


async def _sync_telemetria_all() -> dict:
    total_pos = 0
    total_ev = 0
    async with UnitOfWork(tenant_id=None) as uow:
        tenant_ids = list(
            (
                await uow.session.execute(
                    select(Tenant.id).where(
                        Tenant.status == TenantStatus.ACTIVE, Tenant.deleted_at.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
    for tid in tenant_ids:
        try:
            result = await _sync_telemetria_tenant(tid)
            total_pos += result.get("posicoes", 0)
            total_ev += result.get("eventos", 0)
        except Exception:  # noqa: BLE001
            logger.exception("Falha sync telemetria tenant %s", tid)
    return {"posicoes": total_pos, "eventos": total_ev}


@celery_app.task(name="integracoes.sync_telemetria", queue="integrations")
def sync_telemetria_task() -> dict:
    return asyncio.run(_sync_telemetria_all())
