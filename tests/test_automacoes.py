"""Testes do módulo Automações (§13)."""

from __future__ import annotations

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.automacoes.beat_catalog import list_beat_jobs
from app.modules.automacoes.engine import evaluate_condition
from app.shared.enums import AutoAcaoTipo, AutoEventoGatilho, AutoExecucaoTipo
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

AUTO_PERMS = {
    "dashboard.painel.visualizar",
    "automacoes.regras.visualizar",
    "automacoes.workflows.visualizar",
    "automacoes.agendamentos.visualizar",
    "automacoes.historico.visualizar",
}


def test_permissoes_automacoes_registradas() -> None:
    for code in (
        "automacoes.regras.visualizar",
        "automacoes.regras.executar",
        "automacoes.agendamentos.executar",
        "automacoes.historico.visualizar",
    ):
        assert code in PERMISSIONS_BY_CODE


def test_menu_automacoes_completo() -> None:
    menu = build_menu(_make_user(AUTO_PERMS))
    section = next(s for s in menu if s["label"] == "Automações")
    labels = {item["label"] for item in section["children"]}
    assert labels >= {"Regras", "Workflows", "Agendamentos", "Histórico"}


def test_engine_condicao_always() -> None:
    assert evaluate_condition({"op": "always"}, {}) is True


def test_engine_condicao_gte() -> None:
    cond = {"op": "gte", "field": "dias_vencido", "value": 30}
    assert evaluate_condition(cond, {"dias_vencido": 45}) is True
    assert evaluate_condition(cond, {"dias_vencido": 10}) is False


def test_beat_catalogo_inclui_jobs() -> None:
    jobs = list_beat_jobs()
    assert len(jobs) >= 14
    tasks = {j["task"] for j in jobs}
    assert "automacoes.avaliar_regras" in tasks
    assert "financeiro.marcar_vencidos" in tasks


def test_enums_automacoes() -> None:
    assert AutoEventoGatilho.TITULO_VENCIDO.value == "titulo_vencido"
    assert AutoAcaoTipo.BLOQUEAR_CLIENTE.value == "bloquear_cliente"
    assert AutoExecucaoTipo.BEAT.value == "beat"
