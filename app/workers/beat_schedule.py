"""Agendamentos periódicos do Celery Beat (cron)."""

from __future__ import annotations

from celery.schedules import crontab

BEAT_SCHEDULE: dict[str, dict] = {
    # Expurga registros de auditoria além do período de retenção (LGPD).
    "purge-old-audit-logs": {
        "task": "audit.purge_old_logs",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "maintenance"},
    },
}
