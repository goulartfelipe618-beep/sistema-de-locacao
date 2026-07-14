"""Tarefas de background do módulo de Auditoria.

Usa uma conexão **síncrona** (psycopg) dedicada ao worker Celery, isolada do
engine assíncrono da aplicação web.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from celery.signals import worker_shutdown
from sqlalchemy import create_engine, delete

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.audit.models import AuditLog
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

# Engine síncrono exclusivo do worker (pool pequeno; descartado no shutdown).
_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True, pool_size=2)


@worker_shutdown.connect
def _dispose_sync_engine(**_kwargs: object) -> None:
    """Libera o pool síncrono ao encerrar o worker Celery."""
    _sync_engine.dispose()
    logger.info("Engine síncrono do worker Celery descartado.")


@celery_app.task(name="audit.purge_old_logs", queue="maintenance")
def purge_old_logs() -> int:
    """Remove registros de auditoria mais antigos que o período de retenção.

    Returns:
        Quantidade de registros removidos.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(days=settings.audit_retention_days)
    with _sync_engine.begin() as conn:
        result = conn.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        removed = result.rowcount or 0
    logger.info("Auditoria: %d registro(s) expurgado(s) (corte em %s).", removed, cutoff.date())
    return removed
