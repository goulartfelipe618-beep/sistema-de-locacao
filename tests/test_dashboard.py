"""Testes do Dashboard (§1)."""

from __future__ import annotations

from app.modules.dashboard.service import DashboardSnapshot
from app.modules.automacoes.beat_catalog import list_beat_jobs


def test_dashboard_snapshot_defaults() -> None:
    snap = DashboardSnapshot()
    assert snap.total_users == 0
    assert snap.frota is None
    assert snap.alertas == []


def test_beat_inclui_dashboard_kpis() -> None:
    tasks = {j["task"] for j in list_beat_jobs()}
    assert "dashboard.materializar_kpis" in tasks
