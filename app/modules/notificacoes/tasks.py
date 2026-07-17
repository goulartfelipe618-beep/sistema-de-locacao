"""Tarefas Celery do módulo Notificações (fila ``notifications``)."""

from __future__ import annotations

import asyncio
import uuid

from app.core.database import UnitOfWork
from app.modules.notificacoes.service import NotificationService
from app.workers.celery_app import celery_app


@celery_app.task(name="notificacoes.enviar", queue="notifications", bind=True)
def enviar_notificacao_task(self, envio_id: str, tenant_id: str) -> dict[str, str]:
    """Processa envio pendente de e-mail/SMS."""

    async def _run() -> None:
        async with UnitOfWork(tenant_id=uuid.UUID(tenant_id)) as uow:
            await NotificationService(uow.session)._processar_envio(uuid.UUID(envio_id))

    asyncio.run(_run())
    return {"status": "ok", "envio_id": envio_id}
