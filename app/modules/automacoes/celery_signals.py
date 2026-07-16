"""Sinais Celery para registrar execuções Beat no histórico (§13.4)."""

from __future__ import annotations

import asyncio

from celery.signals import task_failure, task_success

from app.core.config import settings
from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.automacoes.beat_catalog import list_beat_jobs
from app.modules.tenants.repository import TenantRepository

logger = get_logger(__name__)

_BEAT_TASK_NAMES = {job["task"] for job in list_beat_jobs()}


def _resolve_default_tenant_id() -> str | None:
    try:
        return asyncio.run(_async_default_tenant_id())
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao resolver tenant para log Beat")
        return None


async def _async_default_tenant_id():
    async with UnitOfWork(tenant_id=None) as uow:
        tenant = await TenantRepository(uow.session).get_by_slug(settings.default_tenant_slug)
        return str(tenant.id) if tenant else None


@task_success.connect
def _on_task_success(sender=None, result=None, **kwargs) -> None:
    task_name = getattr(sender, "name", None)
    if task_name not in _BEAT_TASK_NAMES:
        return
    tenant_raw = _resolve_default_tenant_id()
    if not tenant_raw:
        return

    async def _log():
        import uuid

        from app.modules.automacoes.service import BeatAdminService

        async with UnitOfWork(tenant_id=uuid.UUID(tenant_raw)) as uow:
            await BeatAdminService.log_beat_conclusao(
                uow.session,
                uuid.UUID(tenant_raw),
                task_name,
                sucesso=True,
                resultado=result if isinstance(result, dict) else {"result": str(result)},
            )

    try:
        asyncio.run(_log())
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar sucesso Beat %s", task_name)


@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None, **kwargs) -> None:
    task_name = getattr(sender, "name", None)
    if task_name not in _BEAT_TASK_NAMES:
        return
    tenant_raw = _resolve_default_tenant_id()
    if not tenant_raw:
        return

    async def _log():
        import uuid

        from app.modules.automacoes.service import BeatAdminService

        async with UnitOfWork(tenant_id=uuid.UUID(tenant_raw)) as uow:
            await BeatAdminService.log_beat_conclusao(
                uow.session,
                uuid.UUID(tenant_raw),
                task_name,
                sucesso=False,
                erro=str(exception),
            )

    try:
        asyncio.run(_log())
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar erro Beat %s", task_name)
