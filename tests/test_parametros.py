"""Testes do módulo Parâmetros (§14.5)."""

from __future__ import annotations

from decimal import Decimal

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.parametros.catalog import CATALOG_BY_KEY, PARAM_CATALOG
from app.modules.parametros.service import _parse_value, _serialize_value, _validate_value
from app.web.navigation import build_menu
from app.shared.enums import ParametroTipo
from tests.test_navigation import _make_user


def test_permissoes_parametros_registradas() -> None:
    for code in (
        "configuracoes.parametro.visualizar",
        "configuracoes.parametro.editar",
    ):
        assert code in PERMISSIONS_BY_CODE


def test_catalogo_parametros_categorias() -> None:
    assert len(PARAM_CATALOG) >= 15
    chaves = {p.chave for p in PARAM_CATALOG}
    assert "geral.prefixo_reserva" in chaves
    assert "cadastros.dias_bloqueio_inadimplencia" in chaves
    assert "auditoria.retencao_anos" in chaves


def test_menu_parametros_habilitado_com_permissao() -> None:
    menu = build_menu(
        _make_user(
            {
                "dashboard.painel.visualizar",
                "configuracoes.parametro.visualizar",
            }
        )
    )
    config = next(s for s in menu if s["label"] == "Configurações")
    parametros = next(item for item in config["children"] if item["label"] == "Parâmetros")
    assert parametros["enabled"] is True
    assert parametros["url"] == "/configuracoes/parametros"


def test_serialize_parse_int() -> None:
    definition = CATALOG_BY_KEY["reservas.buffer_horas"]
    raw = _serialize_value(3, ParametroTipo.INT)
    assert _parse_value(raw, ParametroTipo.INT) == 3
    _validate_value(3, definition)


def test_serialize_parse_decimal() -> None:
    definition = CATALOG_BY_KEY["manutencao.os_valor_aprovacao"]
    raw = _serialize_value("7500.50", ParametroTipo.DECIMAL)
    assert _parse_value(raw, ParametroTipo.DECIMAL) == Decimal("7500.50")
    _validate_value("7500.50", definition)


def test_validacao_dia_fechamento() -> None:
    definition = CATALOG_BY_KEY["financeiro.dia_fechamento"]
    _validate_value(15, definition)
