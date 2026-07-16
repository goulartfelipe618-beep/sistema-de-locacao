"""Tarefas Celery do motor de PDF (§16)."""

from __future__ import annotations

import asyncio
import uuid

from app.core.database import UnitOfWork
from app.modules.documentos.service import ReportService
from app.workers.celery_app import celery_app


@celery_app.task(name="documentos.gerar_pdf", bind=True)
def gerar_pdf_task(self, documento_id: str, tenant_id: str) -> dict[str, str]:
    """Processa geração assíncrona de PDF."""

    async def _run() -> None:
        async with UnitOfWork(tenant_id=uuid.UUID(tenant_id)) as uow:
            await ReportService(uow.session).processar(uuid.UUID(documento_id))

    asyncio.run(_run())
    return {"status": "ok", "documento_id": documento_id}
