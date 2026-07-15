"""Testes do módulo Locações (transições e menu)."""

from __future__ import annotations

from app.modules.locacoes.service import CONTRATO_TRANSITIONS
from app.shared.enums import ContratoStatus
from app.web.navigation import build_menu
from tests.test_navigation import _make_user


def test_contrato_transitions() -> None:
    assert ContratoStatus.AGUARDANDO_CHECKOUT in CONTRATO_TRANSITIONS[ContratoStatus.RASCUNHO]
    assert ContratoStatus.ATIVO in CONTRATO_TRANSITIONS[ContratoStatus.AGUARDANDO_CHECKOUT]
    assert ContratoStatus.ENCERRADO in CONTRATO_TRANSITIONS.get(
        ContratoStatus.AGUARDANDO_CHECKIN, set()
    ) | CONTRATO_TRANSITIONS.get(ContratoStatus.ATIVO, set())
    assert CONTRATO_TRANSITIONS[ContratoStatus.CANCELADO] == set()


def test_menu_locacoes() -> None:
    perms = {
        "locacoes.contrato.visualizar",
        "locacoes.checkout.visualizar",
        "locacoes.checkin.visualizar",
        "locacoes.renovacao.visualizar",
        "locacoes.encerramento.visualizar",
        "locacoes.multa.visualizar",
        "locacoes.avaria.visualizar",
    }
    menu = build_menu(_make_user(perms))
    section = next(s for s in menu if s["label"] == "Locações")
    by_label = {i["label"]: i for i in section["children"]}
    for label, url in (
        ("Contratos", "/locacoes/contratos"),
        ("Check-out", "/locacoes/checkout"),
        ("Check-in", "/locacoes/checkin"),
        ("Renovações", "/locacoes/renovacoes"),
        ("Encerramentos", "/locacoes/encerramentos"),
        ("Multas e Infrações", "/locacoes/multas"),
        ("Avarias", "/locacoes/avarias"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url
