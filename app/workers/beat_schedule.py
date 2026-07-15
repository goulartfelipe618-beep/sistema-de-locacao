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
    # Vigência documental da frota (§3.7) — alertas operacionais via status Restrito.
    "frota-refresh-documentacao": {
        "task": "frota.refresh_documentacao_vigencias",
        "schedule": crontab(hour=4, minute=15),
        "options": {"queue": "maintenance"},
    },
    # Planos preventivos (§4.2) — gera OS automática ao atingir gatilho.
    "manutencao-avaliar-preventivas": {
        "task": "manutencao.avaliar_preventivas",
        "schedule": crontab(hour=5, minute=0),
        "options": {"queue": "maintenance"},
    },
    # No-show de reservas confirmadas (§5.2).
    "reservas-processar-no-show": {
        "task": "reservas.processar_no_show",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "default"},
    },
    # Expira cotações não convertidas (§5.5).
    "reservas-expirar-cotacoes": {
        "task": "reservas.expirar_cotacoes",
        "schedule": crontab(minute=15),
        "options": {"queue": "default"},
    },
}
