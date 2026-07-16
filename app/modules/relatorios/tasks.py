"""Tarefas Celery do módulo Relatórios (fila ``reports``)."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.relatorios.service import AgendamentoService, EmissaoService
from app.modules.tenants.models import Tenant
from app.shared.enums import TenantStatus
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _processar_emissao(emissao_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        await EmissaoService(uow.session).processar(emissao_id)


async def _processar_agendamentos_tenant(tenant_id: uuid.UUID) -> int:
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        return await AgendamentoService(uow.session).processar_vencidos(tenant_id)


async def _processar_agendamentos_todos() -> dict:
    total = 0
    async with UnitOfWork(tenant_id=None) as uow:
        stmt = select(Tenant.id).where(Tenant.status == TenantStatus.ACTIVE, Tenant.deleted_at.is_(None))
        tenant_ids = list((await uow.session.execute(stmt)).scalars().all())
    for tid in tenant_ids:
        try:
            total += await _processar_agendamentos_tenant(tid)
        except Exception:  # noqa: BLE001
            logger.exception("Falha agendamentos relatórios tenant %s", tid)
    return {"processados": total}


@celery_app.task(name="relatorios.processar_emissao", queue="reports")
def processar_emissao_task(emissao_id: str, tenant_id: str) -> None:
    asyncio.run(_processar_emissao(uuid.UUID(emissao_id), uuid.UUID(tenant_id)))


@celery_app.task(name="relatorios.processar_agendamentos", queue="reports")
def processar_agendamentos_task() -> dict:
    return asyncio.run(_processar_agendamentos_todos())
