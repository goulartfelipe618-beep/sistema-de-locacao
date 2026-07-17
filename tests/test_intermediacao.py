"""Testes do módulo Intermediação — permissões, menu, cálculo de repasse/comissão."""

from __future__ import annotations

from decimal import Decimal

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.intermediacao.service import _money
from app.shared.enums import (
    ModeloNegocioTerceiro,
    ModoOperacaoLocadora,
    TipoCalculoRepasse,
    VeiculoPropriedade,
)
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

INTERMEDIACAO_PERMS = {
    "intermediacao.config.visualizar",
    "intermediacao.contrato.visualizar",
    "intermediacao.indisponibilidade.visualizar",
}


def test_money_helper() -> None:
    assert _money(Decimal("10.5")) == Decimal("10.50")
    assert _money(None) == Decimal("0.00")


def test_intermediacao_permissions_registradas() -> None:
    for code in INTERMEDIACAO_PERMS:
        assert code in PERMISSIONS_BY_CODE
    assert "intermediacao.config.editar" in PERMISSIONS_BY_CODE
    assert "intermediacao.contrato.criar" in PERMISSIONS_BY_CODE
    assert "intermediacao.indisponibilidade.criar" in PERMISSIONS_BY_CODE


def test_menu_intermediacao_enabled() -> None:
    menu = build_menu(_make_user(INTERMEDIACAO_PERMS))
    section = next(s for s in menu if s["label"] == "Intermediação")
    by_label = {i["label"]: i for i in section["children"]}
    for label, url in (
        ("Configurações", "/intermediacao/config"),
        ("Contratos Parceiros", "/intermediacao/contratos-fornecedor"),
        ("Indisponibilidades", "/intermediacao/indisponibilidades"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url


def test_enums_intermediacao() -> None:
    assert ModeloNegocioTerceiro.REPASSE.value == "repasse"
    assert ModeloNegocioTerceiro.COMISSAO.value == "comissao"
    assert ModoOperacaoLocadora.HIBRIDA.value == "hibrida"
    assert TipoCalculoRepasse.TABELA.value == "tabela"
    assert VeiculoPropriedade.TERCEIRIZADA.value == "terceirizada"


def test_repasse_margem_formula() -> None:
    valor_cli = Decimal("1000")
    valor_rep = Decimal("850")
    margem = _money(valor_cli - valor_rep)
    margem_pct = _money(margem / valor_cli * 100)
    assert margem == Decimal("150.00")
    assert margem_pct == Decimal("15.00")


def test_auto_eventos_intermediacao() -> None:
    from app.shared.enums import AutoEventoGatilho

    assert AutoEventoGatilho.INTERMEDIACAO_PENDENTE.value == "intermediacao_pendente"
    assert AutoEventoGatilho.INTERMEDIACAO_APROVADA.value == "intermediacao_aprovada"


def test_api_permissions_extras() -> None:
    assert "intermediacao.repasse.visualizar" in PERMISSIONS_BY_CODE
    assert "intermediacao.reserva.aprovar" in PERMISSIONS_BY_CODE


def test_relatorios_intermediacao_catalogo() -> None:
    from app.modules.relatorios.catalog import REPORT_CATALOG

    assert "intermediacao_margem_parceiro" in REPORT_CATALOG
    assert "intermediacao_repasses_pendentes" in REPORT_CATALOG
