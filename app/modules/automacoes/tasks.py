"""Tarefas Celery do módulo Automações."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.automacoes.service import RegraService, WorkflowService
from app.modules.tenants.models import Tenant
from app.shared.enums import TenantStatus
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _avaliar_regras_tenant(tenant_id: uuid.UUID) -> int:
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        return await RegraService(uow.session).avaliar_periodicas(tenant_id)


async def _avaliar_regras_todos() -> dict:
    total = 0
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
            total += await _avaliar_regras_tenant(tid)
        except Exception:  # noqa: BLE001
            logger.exception("Falha avaliar regras tenant %s", tid)
    return {"disparos": total}


async def _workflows_timeout_todos() -> dict:
    total = 0
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
            async with UnitOfWork(tenant_id=tid) as uow:
                total += await WorkflowService(uow.session).processar_timeouts(tid)
        except Exception:  # noqa: BLE001
            logger.exception("Falha timeout workflows tenant %s", tid)
    return {"processados": total}


@celery_app.task(name="automacoes.avaliar_regras", queue="default")
def avaliar_regras_task() -> dict:
    return asyncio.run(_avaliar_regras_todos())


@celery_app.task(name="automacoes.processar_workflows_timeout", queue="default")
def processar_workflows_timeout_task() -> dict:
    return asyncio.run(_workflows_timeout_todos())


import app.modules.automacoes.celery_signals  # noqa: F401, E402
