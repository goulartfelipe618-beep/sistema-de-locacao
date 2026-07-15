"""Tarefas Celery do módulo Reservas (no-show e expiração de cotações)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.reservas.models import ResReserva
from app.modules.reservas.service import CotacaoService, ReservaService
from app.modules.tenants.models import Tenant
from app.shared.enums import ReservaStatus, TenantStatus
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

DEFAULT_NO_SHOW_HORAS = 2


async def _processar_no_show_tenant(
    tenant_id, *, horas_tolerancia: int = DEFAULT_NO_SHOW_HORAS
) -> int:
    limite = datetime.now(tz=UTC) - timedelta(hours=horas_tolerancia)
    marcadas = 0
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        stmt = select(ResReserva).where(
            ResReserva.status == ReservaStatus.CONFIRMADA,
            ResReserva.retirada_em < limite,
            ResReserva.deleted_at.is_(None),
        )
        reservas = list((await uow.session.execute(stmt)).scalars().all())
        svc = ReservaService(uow.session)
        for reserva in reservas:
            await svc.marcar_no_show(reserva.id)
            marcadas += 1
    return marcadas


async def _expirar_cotacoes_tenant(tenant_id) -> int:
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        return await CotacaoService(uow.session).expirar_vencidas()


async def _no_show_todos_tenants(*, horas_tolerancia: int = DEFAULT_NO_SHOW_HORAS) -> dict:
    total = 0
    tenants = 0
    async with UnitOfWork(tenant_id=None) as uow:
        result = await uow.session.execute(
            select(Tenant.id).where(
                Tenant.status == TenantStatus.ACTIVE,
                Tenant.deleted_at.is_(None),
            )
        )
        tenant_ids = list(result.scalars().all())

    for tenant_id in tenant_ids:
        total += await _processar_no_show_tenant(
            tenant_id, horas_tolerancia=horas_tolerancia
        )
        tenants += 1

    logger.info("No-show processado: tenants=%s reservas=%s", tenants, total)
    return {"tenants": tenants, "no_show": total}


async def _expirar_cotacoes_todos_tenants() -> dict:
    total = 0
    tenants = 0
    async with UnitOfWork(tenant_id=None) as uow:
        result = await uow.session.execute(
            select(Tenant.id).where(
                Tenant.status == TenantStatus.ACTIVE,
                Tenant.deleted_at.is_(None),
            )
        )
        tenant_ids = list(result.scalars().all())

    for tenant_id in tenant_ids:
        total += await _expirar_cotacoes_tenant(tenant_id)
        tenants += 1

    logger.info("Cotações expiradas: tenants=%s cotacoes=%s", tenants, total)
    return {"tenants": tenants, "expiradas": total}


@celery_app.task(name="reservas.processar_no_show", queue="default")
def processar_no_show(horas_tolerancia: int = DEFAULT_NO_SHOW_HORAS) -> dict:
    """Job §5.2: confirmadas sem check-out após retirada + tolerância → no-show."""
    return asyncio.run(_no_show_todos_tenants(horas_tolerancia=horas_tolerancia))


@celery_app.task(name="reservas.expirar_cotacoes", queue="default")
def expirar_cotacoes() -> dict:
    """Job §5.5: cotações abertas vencidas → EXPIRADA."""
    return asyncio.run(_expirar_cotacoes_todos_tenants())
