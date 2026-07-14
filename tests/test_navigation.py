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
    frota = next(s for s in menu if s["label"] == "Frota")
    assert all(item["enabled"] is False for item in frota["items"])
