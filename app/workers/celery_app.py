"""Instância e configuração do Celery.

Define filas segmentadas por prioridade/natureza (prontas para o crescimento do
sistema) e integra o agendador (beat). As tarefas concretas são descobertas nos
módulos (``app.modules.<modulo>.tasks``).
"""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from app.core.config import settings
from app.core.logging import configure_logging
from app.workers.beat_schedule import BEAT_SCHEDULE

configure_logging()

celery_app = Celery(
    "erp_locadora",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.modules.audit.tasks",
        "app.modules.comercial.tasks",
        "app.modules.financeiro.tasks",
        "app.modules.fiscal.tasks",
        "app.modules.integracoes.tasks",
        "app.modules.automacoes.tasks",
        "app.modules.notificacoes.tasks",
        "app.modules.relatorios.tasks",
        "app.modules.documentos.tasks",
        "app.modules.dashboard.tasks",
        "app.modules.frota.tasks",
        "app.modules.manutencao.tasks",
        "app.modules.reservas.tasks",
    ],
)

celery_app.conf.update(
    timezone=settings.timezone,
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=60 * 30,
    task_soft_time_limit=60 * 25,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,
    result_expires=60 * 60 * 24,
    task_default_queue="default",
    task_queues=(
        Queue("critical"),
        Queue("default"),
        Queue("notifications"),
        Queue("reports"),
        Queue("integrations"),
        Queue("maintenance"),
    ),
    beat_schedule=BEAT_SCHEDULE,
)
