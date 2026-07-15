"""Testes do módulo Comercial / CRM (§7): numeração, cupons, funil e menu."""

from __future__ import annotations

from decimal import Decimal

from app.modules.comercial.models import CrmCupom
from app.modules.comercial.service import (
    KANBAN_ESTAGIOS,
    CupomService,
    _money,
)
from app.shared.enums import (
    CrmCupomTipo,
    CrmEstagio,
    CrmPropostaStatus,
)
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

COMERCIAL_PERMS = {
    "comercial.funil.visualizar",
    "comercial.proposta.visualizar",
    "comercial.campanha.visualizar",
    "comercial.cupom.visualizar",
    "comercial.fidelidade.visualizar",
}


def test_kanban_estagios_ordem() -> None:
    assert KANBAN_ESTAGIOS[0] == CrmEstagio.LEAD
    assert CrmEstagio.FECHADO_GANHO in KANBAN_ESTAGIOS
    assert CrmEstagio.PERDIDO in KANBAN_ESTAGIOS
    assert len(KANBAN_ESTAGIOS) == len(set(KANBAN_ESTAGIOS)) == 6


def test_numeracao_formats() -> None:
    assert f"OPP-{1:06d}" == "OPP-000001"
    assert f"PROP-{42:06d}" == "PROP-000042"
    assert f"CAMP-{7:06d}" == "CAMP-000007"


def test_money_quantize() -> None:
    assert _money(Decimal("10")) == Decimal("10.00")
    assert _money(Decimal("10.1")) == Decimal("10.10")


def _cupom(tipo: CrmCupomTipo, valor: Decimal) -> CrmCupom:
    return CrmCupom(codigo="TEST", tipo=tipo, valor=valor)


def test_cupom_desconto_percentual() -> None:
    svc = CupomService(session=None)  # type: ignore[arg-type]
    cupom = _cupom(CrmCupomTipo.PERCENTUAL, Decimal("10"))
    assert svc._calcular_desconto(cupom, Decimal("200")) == Decimal("20.00")


def test_cupom_desconto_valor_fixo_capped() -> None:
    svc = CupomService(session=None)  # type: ignore[arg-type]
    cupom = _cupom(CrmCupomTipo.VALOR_FIXO, Decimal("500"))
    # O desconto nunca ultrapassa o valor base.
    assert svc._calcular_desconto(cupom, Decimal("300")) == Decimal("300.00")


def test_proposta_status_terminais() -> None:
    assert CrmPropostaStatus.ACEITA.value == "aceita"
    assert CrmPropostaStatus.EXPIRADA.value == "expirada"


def test_menu_comercial_enabled() -> None:
    menu = build_menu(_make_user(COMERCIAL_PERMS))
    section = next(s for s in menu if s["label"] == "Comercial / CRM")
    by_label = {i["label"]: i for i in section["children"]}
    for label, url in (
        ("Funil de Vendas", "/comercial/funil"),
        ("Propostas", "/comercial/propostas"),
        ("Campanhas", "/comercial/campanhas"),
        ("Cupons", "/comercial/cupons"),
        ("Fidelidade", "/comercial/fidelidade"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url


def test_menu_comercial_partial_permissions() -> None:
    menu = build_menu(_make_user({"comercial.funil.visualizar"}))
    section = next(s for s in menu if s["label"] == "Comercial / CRM")
    labels = {i["label"] for i in section["children"]}
    assert labels == {"Funil de Vendas"}
