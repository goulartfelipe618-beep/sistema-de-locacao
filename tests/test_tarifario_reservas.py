"""Testes de Tarifário e Reservas (menus, status, pricing imports)."""

from __future__ import annotations

from app.modules.reservas.service import RESERVA_TRANSITIONS
from app.modules.tarifario.service import PricingService
from app.shared.enums import ReservaStatus
from app.web.navigation import build_menu
from tests.test_navigation import _make_user


def test_pricing_service_exportado() -> None:
    assert hasattr(PricingService, "calcular")
    assert hasattr(PricingService, "simular_cancelamento")
    assert hasattr(PricingService, "ensure_defaults")


def test_reserva_transitions() -> None:
    assert ReservaStatus.CONFIRMADA in RESERVA_TRANSITIONS[ReservaStatus.PENDENTE]
    assert ReservaStatus.CANCELADA in RESERVA_TRANSITIONS[ReservaStatus.CONFIRMADA]
    assert RESERVA_TRANSITIONS[ReservaStatus.CONCLUIDA] == set()


def test_menu_tarifario_e_reservas() -> None:
    perms = {
        "tarifario.tabela.visualizar",
        "tarifario.temporada.visualizar",
        "tarifario.taxa.visualizar",
        "tarifario.protecao.visualizar",
        "tarifario.politica.visualizar",
        "tarifario.simular.visualizar",
        "reservas.reserva.visualizar",
        "reservas.reserva.criar",
        "reservas.calendario.visualizar",
        "reservas.disponibilidade.visualizar",
        "reservas.cotacao.visualizar",
    }
    menu = build_menu(_make_user(perms))
    labels = {s["label"]: s for s in menu}

    tar = {i["label"]: i for i in labels["Tarifário"]["children"]}
    assert tar["Tabelas de Tarifas"]["enabled"] is True
    assert tar["Simular Preço"]["url"] == "/tarifario/simular"

    res = {i["label"]: i for i in labels["Reservas"]["children"]}
    assert res["Nova Reserva"]["enabled"] is True
    assert res["Disponibilidade"]["url"] == "/reservas/disponibilidade"
    assert res["Cotações"]["enabled"] is True
