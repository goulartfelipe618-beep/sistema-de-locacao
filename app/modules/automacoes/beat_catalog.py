"""Catálogo legível dos jobs Celery Beat (§13.3)."""

from __future__ import annotations

from app.workers.beat_schedule import BEAT_SCHEDULE

_LABELS: dict[str, tuple[str, str]] = {
    "purge-old-audit-logs": ("Expurgo de auditoria", "Remove logs além do período de retenção (LGPD)"),
    "frota-refresh-documentacao": ("Vigência documental", "Atualiza alertas de documentação da frota (§3.7)"),
    "manutencao-avaliar-preventivas": ("Preventivas", "Gera OS automática ao atingir gatilho (§4.2)"),
    "reservas-processar-no-show": ("No-show reservas", "Marca reservas confirmadas como no-show (§5.2)"),
    "reservas-expirar-cotacoes": ("Expirar cotações", "Expira cotações não convertidas (§5.5)"),
    "financeiro-marcar-vencidos": ("Títulos vencidos", "Marca CR/CP vencidos (§9.2/§9.3)"),
    "financeiro-expirar-pix": ("Expirar PIX", "Expira cobranças PIX pendentes (§9.4)"),
    "financeiro-fechar-faturamento": ("Fechar faturamento", "Fecha ciclos consolidados (§9.8)"),
    "comercial-expirar-propostas": ("Expirar propostas", "Propostas com validade vencida (§7.2)"),
    "comercial-expirar-pontos-fidelidade": ("Expirar pontos", "Pontos de fidelidade vencidos (§7.5)"),
    "comercial-alertar-funil-parado": ("Funil parado", "Alerta oportunidades paradas (§7.1)"),
    "relatorios-processar-agendamentos": ("Relatórios agendados", "Processa agendamentos de relatórios (§11)"),
    "integracoes-sync-telemetria": ("Sync telemetria", "Sincroniza telemetria externa (§12.4)"),
    "automacoes-avaliar-regras": ("Avaliar regras", "Executa regras periódicas de automação (§13.1)"),
    "automacoes-workflows-timeout": ("Timeout workflows", "Processa SLAs expirados de workflows (§13.2)"),
}


def _schedule_label(schedule: object) -> str:
    return str(schedule)


def list_beat_jobs() -> list[dict]:
    """Retorna metadados dos jobs registrados no Beat."""
    items: list[dict] = []
    for key, cfg in BEAT_SCHEDULE.items():
        label, desc = _LABELS.get(key, (key, ""))
        items.append(
            {
                "key": key,
                "nome": label,
                "descricao": desc,
                "task": cfg["task"],
                "schedule": _schedule_label(cfg["schedule"]),
                "queue": cfg.get("options", {}).get("queue", "default"),
            }
        )
    return sorted(items, key=lambda x: x["nome"])


def get_beat_job(key: str) -> dict | None:
    for job in list_beat_jobs():
        if job["key"] == key:
            return job
    return None
