"""Tarefas Celery do Dashboard (§1)."""

from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="dashboard.materializar_kpis", bind=True)
def materializar_kpis(self) -> dict[str, str]:
    """Job periódico de atualização dos KPIs (agregação sob demanda na UI).

    Mantido como heartbeat operacional; futuras versões podem persistir cache
    materializado por tenant/filial.
    """
    return {"status": "ok", "task": self.name}
