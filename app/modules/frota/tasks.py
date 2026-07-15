"""Tarefas Celery do módulo Frota (vigência documental e restrição)."""

from __future__ import annotations

from celery.signals import worker_shutdown
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True, pool_size=2)


@worker_shutdown.connect
def _dispose_sync_engine(**_kwargs: object) -> None:
    _sync_engine.dispose()
    logger.info("Engine síncrono Frota descartado.")


@celery_app.task(name="frota.refresh_documentacao_vigencias", queue="maintenance")
def refresh_documentacao_vigencias() -> dict[str, int]:
    """Recalcula status documental e aplica Restrito em veículos elegíveis.

    Job diário conforme §3.7: marca Regular / A vencer / Vencido e integra com
    o status operacional do veículo (Restrito quando há documento vencido).
    """
    updated_docs = 0
    restricted = 0
    released = 0
    with _sync_engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE frota_documentos
                SET status = CASE
                    WHEN data_validade IS NULL THEN 'regular'
                    WHEN data_validade < CURRENT_DATE THEN 'vencido'
                    WHEN data_validade <= CURRENT_DATE + INTERVAL '30 days' THEN 'a_vencer'
                    ELSE 'regular'
                END,
                updated_at = NOW()
                WHERE deleted_at IS NULL
                """
            )
        )
        updated_docs = result.rowcount or 0

        result = conn.execute(
            text(
                """
                UPDATE frota_veiculos v
                SET status = 'restrito',
                    updated_at = NOW()
                WHERE v.deleted_at IS NULL
                  AND v.status IN ('disponivel', 'reservado', 'restrito')
                  AND EXISTS (
                    SELECT 1 FROM frota_documentos d
                    WHERE d.veiculo_id = v.id
                      AND d.deleted_at IS NULL
                      AND d.status = 'vencido'
                  )
                  AND v.status <> 'restrito'
                """
            )
        )
        restricted = result.rowcount or 0

        result = conn.execute(
            text(
                """
                UPDATE frota_veiculos v
                SET status = 'disponivel',
                    updated_at = NOW()
                WHERE v.deleted_at IS NULL
                  AND v.status = 'restrito'
                  AND NOT EXISTS (
                    SELECT 1 FROM frota_documentos d
                    WHERE d.veiculo_id = v.id
                      AND d.deleted_at IS NULL
                      AND d.status = 'vencido'
                  )
                """
            )
        )
        released = result.rowcount or 0

    logger.info(
        "Frota docs refresh: docs=%s restritos=%s liberados=%s",
        updated_docs,
        restricted,
        released,
    )
    return {
        "documentos_atualizados": updated_docs,
        "veiculos_restritos": restricted,
        "veiculos_liberados": released,
    }
