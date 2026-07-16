"""Testes do Dashboard (§1)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.dashboard.cache import decode_snapshot_dict, encode_snapshot, snapshot_asdict
from app.modules.dashboard.service import (
    ComercialKpis,
    DashboardSnapshot,
    FinanceiroKpis,
    FrotaKpis,
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


def test_dashboard_cache_roundtrip() -> None:
    original = DashboardSnapshot(
        total_users=5,
        frota=FrotaKpis(
            total=10,
            disponiveis=4,
            locados=5,
            manutencao=1,
            bloqueados=0,
            ocupacao_pct=62.5,
        ),
        financeiro=FinanceiroKpis(
            faturamento_dia=Decimal("100"),
            faturamento_mes=Decimal("5000"),
            receber_aberto=Decimal("200"),
            receber_vencido=Decimal("50"),
            pagar_aberto=Decimal("80"),
            pagar_vencido=Decimal("10"),
            saldo_caixa=Decimal("1500.50"),
        ),
        ocupacao_30=[OcupacaoPonto(label="01/07", pct=70.0)],
    )
    encoded = encode_snapshot(original)
    restored = decode_snapshot_dict(encoded, DashboardSnapshot)
    assert restored.total_users == 5
    assert restored.frota is not None
    assert restored.frota.locados == 5
    assert restored.financeiro is not None
    assert restored.financeiro.saldo_caixa == Decimal("1500.50")
    assert restored.ocupacao_30[0].pct == 70.0


def test_dashboard_filter_snapshot() -> None:
    from app.modules.dashboard.service import DashboardService

    snap = DashboardSnapshot(
        total_users=1,
        frota=FrotaKpis(1, 1, 0, 0, 0, 0.0),
        financeiro=FinanceiroKpis(
            Decimal(0),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            Decimal(100),
        ),
    )
    svc = DashboardService.__new__(DashboardService)
    filtered = svc.filter_snapshot(snap, permissions={"frota.veiculo.visualizar"})
    assert filtered.frota is not None
    assert filtered.financeiro is None
