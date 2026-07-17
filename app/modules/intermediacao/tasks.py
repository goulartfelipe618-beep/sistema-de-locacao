"""Tarefas Celery — intermediação (site sync, lembretes de aprovação)."""

from __future__ import annotations

import asyncio
import uuid

from app.core.logging import get_logger
from app.core.database import UnitOfWork
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="intermediacao.sincronizar_site", queue="integrations")
def sincronizar_site_task(tenant_id: str | None = None) -> dict:
    """Sincroniza publicar_site de veículos terceirizados para todos ou um tenant."""

    async def _run() -> dict:
        from sqlalchemy import select

        from app.modules.intermediacao.service import IntermediacaoService
        from app.modules.tenants.models import Tenant

        total = {"tenants": 0, "publicados": 0, "ocultos": 0}
        async with UnitOfWork() as uow:
            if tenant_id:
                tid = uuid.UUID(tenant_id)
                svc = IntermediacaoService(uow.session)
                stats = await svc.sincronizar_catalogo_site(tid)
                total["tenants"] = 1
                total["publicados"] += stats["publicados"]
                total["ocultos"] += stats["ocultos"]
                await uow.commit()
                return total
            tenants = list(
                (await uow.session.execute(select(Tenant).where(Tenant.deleted_at.is_(None)))).scalars().all()
            )
            svc = IntermediacaoService(uow.session)
            for t in tenants:
                stats = await svc.sincronizar_catalogo_site(t.id)
                total["tenants"] += 1
                total["publicados"] += stats["publicados"]
                total["ocultos"] += stats["ocultos"]
            await uow.commit()
        return total

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("intermediacao.sincronizar_site falhou: %s", exc)
        raise


@celery_app.task(name="intermediacao.lembrete_aprovacao", queue="notifications")
def lembrete_aprovacao_task() -> dict:
    """Reenvia lembrete de reservas aguardando aprovação da locadora parceira."""

    async def _run() -> dict:
        from sqlalchemy import select

        from app.modules.intermediacao.service import IntermediacaoService
        from app.modules.reservas.models import ResReserva
        from app.modules.tenants.models import Tenant

        enviados = 0
        async with UnitOfWork() as uow:
            tenants = list(
                (await uow.session.execute(select(Tenant).where(Tenant.deleted_at.is_(None)))).scalars().all()
            )
            svc = IntermediacaoService(uow.session)
            for t in tenants:
                pendentes = await svc.list_aprovacoes_pendentes(t.id)
                for reserva in pendentes:
                    await svc.notificar_pendencia_fornecedor(reserva)
                    enviados += 1
            await uow.commit()
        return {"lembretes": enviados}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("intermediacao.lembrete_aprovacao falhou: %s", exc)
        raise
