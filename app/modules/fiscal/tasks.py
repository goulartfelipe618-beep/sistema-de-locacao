"""Tarefas Celery do módulo Fiscal (§10).

Jobs periódicos:
    * Reprocessar documentos fiscais rejeitados (reenvio ao provedor simulado).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.fiscal.service import NfeService, NfseService
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
                Tenant.fiscal_emissao_habilitada.is_(True),
            )
        )
        return list(result.scalars().all())


async def _reprocessar_rejeitadas_all() -> dict:
    nfse_total = 0
    nfe_total = 0
    tenants = 0
    for tenant_id in await _tenant_ids():
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            nfse_total += await NfseService(uow.session).reprocessar_rejeitadas()
            nfe_total += await NfeService(uow.session).reprocessar_rejeitadas()
        tenants += 1
    logger.info(
        "Fiscal reprocessadas: tenants=%s nfse=%s nfe=%s", tenants, nfse_total, nfe_total
    )
    return {"tenants": tenants, "nfse": nfse_total, "nfe": nfe_total}


@celery_app.task(name="fiscal.reprocessar_rejeitadas", queue="default")
def reprocessar_rejeitadas() -> dict:
    """Job §10: reenvia NFS-e/NF-e rejeitadas ao provedor (simulado)."""
    return asyncio.run(_reprocessar_rejeitadas_all())
