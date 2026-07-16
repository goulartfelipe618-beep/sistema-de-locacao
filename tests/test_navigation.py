"""Testes da construção da árvore de navegação (RBAC + amplitude)."""

from __future__ import annotations

import uuid

from app.modules.identity.service import AuthenticatedUser
from app.web.navigation import build_menu


def _make_user(permissions: set[str], is_superuser: bool = False) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="u@x.com",
        full_name="Teste",
        is_active=True,
        is_superuser=is_superuser,
        roles=[],
        permissions=permissions,
        filial_ids=[],
    )


def test_anonymous_has_no_menu() -> None:
    assert build_menu(None) == []


def test_superuser_sees_dashboard_enabled() -> None:
    menu = build_menu(_make_user(set(), is_superuser=True))
    dashboard = next(s for s in menu if s["label"] == "Dashboard")
    assert dashboard["enabled"] is True


def test_operator_without_dashboard_permission_hides_it() -> None:
    menu = build_menu(_make_user(set()))
    labels = [s["label"] for s in menu]
    assert "Dashboard" not in labels


def test_future_modules_visible_but_disabled() -> None:
    menu = build_menu(_make_user({"dashboard.painel.visualizar"}))
    config = next(s for s in menu if s["label"] == "Configurações")
    parametros = next(item for item in config["children"] if item["label"] == "Parâmetros")
    assert parametros["enabled"] is False


def test_automacoes_enabled_with_permissions() -> None:
    menu = build_menu(
        _make_user(
            {
                "dashboard.painel.visualizar",
                "automacoes.regras.visualizar",
                "automacoes.historico.visualizar",
            }
        )
    )
    auto = next(s for s in menu if s["label"] == "Automações")
    enabled = {item["label"] for item in auto["children"] if item["enabled"]}
    assert {"Regras", "Histórico"} <= enabled


def test_integracoes_enabled_with_permissions() -> None:
    menu = build_menu(
        _make_user(
            {
                "dashboard.painel.visualizar",
                "integracoes.pagamentos.visualizar",
                "integracoes.api_publica.visualizar",
            }
        )
    )
    integracoes = next(s for s in menu if s["label"] == "Integrações")
    enabled = {item["label"] for item in integracoes["children"] if item["enabled"]}
    assert {"Pagamentos", "API Pública"} <= enabled


def test_relatorios_enabled_with_permissions() -> None:
    menu = build_menu(
        _make_user(
            {
                "dashboard.painel.visualizar",
                "relatorios.frota.visualizar",
                "relatorios.historico.visualizar",
            }
        )
    )
    relatorios = next(s for s in menu if s["label"] == "Relatórios")
    enabled = {item["label"] for item in relatorios["children"] if item["enabled"]}
    assert {"Frota", "Histórico"} <= enabled


def test_comercial_hidden_without_permissions() -> None:
    # Comercial / CRM agora é implementado e depende de permissões: sem elas a
    # seção não aparece para o usuário.
    menu = build_menu(_make_user({"dashboard.painel.visualizar"}))
    labels = [s["label"] for s in menu]
    assert "Comercial / CRM" not in labels


def test_financeiro_enabled_with_permissions() -> None:
    menu = build_menu(
        _make_user(
            {
                "dashboard.painel.visualizar",
                "financeiro.caixa.visualizar",
                "financeiro.receber.visualizar",
            }
        )
    )
    financeiro = next(s for s in menu if s["label"] == "Financeiro")
    enabled = {item["label"] for item in financeiro["children"] if item["enabled"]}
    assert {"Caixa", "Contas a Receber"} <= enabled
