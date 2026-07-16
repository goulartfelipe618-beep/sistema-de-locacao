"""Testes do Dashboard (§1)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.dashboard.service import (
    ComercialKpis,
    DashboardSnapshot,
    FinanceiroKpis,
    ManutencaoKpis,
    OcupacaoPonto,
)
from app.modules.automacoes.beat_catalog import list_beat_jobs


def test_dashboard_snapshot_defaults() -> None:
    snap = DashboardSnapshot()
    assert snap.total_users == 0
    assert snap.frota is None
    assert snap.alertas == []


def test_beat_inclui_dashboard_kpis() -> None:
    tasks = {j["task"] for j in list_beat_jobs()}
    assert "dashboard.materializar_kpis" in tasks


def test_dashboard_kpi_dataclasses_extendidos() -> None:
    fin = FinanceiroKpis(
        faturamento_dia=Decimal("10"),
        faturamento_mes=Decimal("100"),
        receber_aberto=Decimal("50"),
        receber_vencido=Decimal("5"),
        pagar_aberto=Decimal("20"),
        pagar_vencido=Decimal("2"),
        saldo_caixa=Decimal("1500"),
    )
    assert fin.saldo_caixa == Decimal("1500")

    man = ManutencaoKpis(
        os_abertas=3,
        aguardando_aprovacao=1,
        preventiva_pendente=2,
        pneus_alerta=4,
    )
    assert man.pneus_alerta == 4

    com = ComercialKpis(
        oportunidades_abertas=10,
        propostas_abertas=5,
        propostas_aceitas_mes=2,
        taxa_conversao_pct=66.7,
        funil_por_estagio={"lead": 3, "negociacao": 2},
    )
    assert com.funil_por_estagio["lead"] == 3

    snap = DashboardSnapshot(
        ocupacao_30=[OcupacaoPonto(label="01/07", pct=72.5)],
        ocupacao_90=[OcupacaoPonto(label="15/04", pct=65.0)],
    )
    assert len(snap.ocupacao_30) == 1
    assert snap.ocupacao_90[0].pct == 65.0
