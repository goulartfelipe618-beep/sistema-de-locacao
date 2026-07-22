"""Testes da construção da árvore de navegação (RBAC + amplitude)."""

from __future__ import annotations

import uuid

from app.modules.identity.service import AuthenticatedUser
from app.web.navigation import build_menu, resolve_active_menu_url


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


def test_parametros_hidden_without_permission() -> None:
    menu = build_menu(
        _make_user(
            {
                "dashboard.painel.visualizar",
                "configuracoes.empresa.visualizar",
            }
        )
    )
    config = next(s for s in menu if s["label"] == "Configurações")
    labels = {item["label"] for item in config["children"]}
    assert "Parâmetros" not in labels


def test_parametros_enabled_with_permission() -> None:
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


def test_resolve_active_menu_url_longest_prefix() -> None:
    menu = build_menu(_make_user(set(), is_superuser=True))
    assert resolve_active_menu_url("/reservas/calendario", menu) == "/reservas/calendario"
    assert resolve_active_menu_url("/reservas", menu) == "/reservas"
    assert resolve_active_menu_url("/frota/veiculos", menu) == "/frota/veiculos"
    assert resolve_active_menu_url("/frota/veiculos/novo", menu) == "/frota/veiculos"
    assert resolve_active_menu_url("/inexistente", menu) is None


def test_spa_request_returns_app_content_fragment(client) -> None:
    login = client.get("/login")
    import re

    m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    client.post(
        "/login",
        data={"email": "admin@locadora.local", "password": "Admin@123", "csrf_token": m.group(1)},
        follow_redirects=True,
    )
    full = client.get("/frota/veiculos")
    assert full.status_code == 200
    assert "<!DOCTYPE html>" in full.text
    assert 'id="app-content"' in full.text

    spa = client.get("/frota/veiculos", headers={"X-ERP-SPA": "1"})
    assert spa.status_code == 200
    assert "<!DOCTYPE html>" not in spa.text
    assert spa.text.strip().startswith("<main")
    assert 'id="app-content"' in spa.text

    spa_categorias = client.get("/frota/categorias", headers={"X-ERP-SPA": "1"})
    assert spa_categorias.status_code == 200
    assert "Veículos" not in spa_categorias.text or "Categorias" in spa_categorias.text
