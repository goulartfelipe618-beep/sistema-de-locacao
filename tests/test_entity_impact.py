"""Testes de consulta de impacto entre entidades."""

from __future__ import annotations

from app.main import app
from app.shared.entity_impact import _build_summary


def test_impact_routes_registered() -> None:
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/cadastros/clientes/{cliente_id}/impacto" in paths
    assert "/cadastros/motoristas/{item_id}/impacto" in paths
    assert "/frota/veiculos/{veiculo_id}/impacto" in paths


def test_build_summary_blocked() -> None:
    details = [
        {"label": "Contratos ativos", "count": 2},
        {"label": "Reservas abertas", "count": 1},
    ]
    msg = _build_summary("cliente", details, blocked=True)
    assert "Não é possível prosseguir" in msg
    assert "2 contratos ativos" in msg
    assert "1 reservas abertas" in msg


def test_build_summary_warn_only() -> None:
    details = [{"label": "Títulos em aberto", "count": 3}]
    msg = _build_summary("cliente", details, blocked=False)
    assert "Atenção" in msg
    assert "3 títulos em aberto" in msg


def test_build_summary_clean() -> None:
    details = [
        {"label": "Contratos ativos", "count": 0},
        {"label": "Reservas abertas", "count": 0},
    ]
    msg = _build_summary("veículo", details, blocked=False)
    assert "Nenhum vínculo crítico" in msg
