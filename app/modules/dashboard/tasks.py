"""Tarefas Celery do Dashboard (§1)."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.core.pagination import PageParams
from app.modules.dashboard.cache import save_snapshot_cache
from app.modules.dashboard.service import DashboardService
from app.modules.parametros.service import ParametroService
from app.modules.tenants.models import Tenant
from app.modules.tenants.service import FilialService
from app.shared.enums import FilialStatus, TenantStatus
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _materializar_todos_tenants() -> dict[str, int]:
    materializados = 0
    tenants_processados = 0

    async with UnitOfWork(tenant_id=None) as uow:
        tenant_ids = list(
            (
                await uow.session.execute(
                    select(Tenant.id).where(
                        Tenant.status == TenantStatus.ACTIVE,
                        Tenant.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )

    for tenant_id in tenant_ids:
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            svc = DashboardService(uow.session)
            param_svc = ParametroService(uow.session)
            refresh_min = int(
                await param_svc.get_valor("geral.dashboard_refresh_minutos", tenant_id, None)
            )
            ttl_seconds = max(refresh_min * 60 * 2, 900)

            filiais = await FilialService(uow.session).list_filiais(
                PageParams(page=1, size=200)
            )
            filial_ids: list[uuid.UUID | None] = [None]
            filial_ids.extend(
                f.id
                for f in filiais.items
                if f.deleted_at is None and f.status == FilialStatus.ACTIVE
            )

            for filial_id in filial_ids:
                snap = await svc.build_raw_snapshot(filial_id)
                await save_snapshot_cache(
                    tenant_id,
                    filial_id,
                    snap,
                    ttl_seconds=ttl_seconds,
                )
                materializados += 1

            tenants_processados += 1

    logger.info(
        "Dashboard KPIs materializados: tenants=%s chaves=%s",
        tenants_processados,
        materializados,
    )
    return {"tenants": tenants_processados, "materializados": materializados}


@celery_app.task(name="dashboard.materializar_kpis", bind=True)
def materializar_kpis(self) -> dict[str, int]:
    """Job periódico: persiste agregações do painel no Redis por tenant/filial."""
    return asyncio.run(_materializar_todos_tenants())
