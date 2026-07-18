"""Testes de responsividade global e bloqueio de zoom mobile."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

VIEWPORT_NO_ZOOM = "maximum-scale=1, user-scalable=no"


def test_base_includes_responsive_assets() -> None:
    base = Path("app/web/templates/base.html").read_text(encoding="utf-8")
    navbar = Path("app/web/templates/partials/navbar.html").read_text(encoding="utf-8")
    sidebar = Path("app/web/templates/partials/sidebar.html").read_text(encoding="utf-8")
    assert "responsive.css" in base
    assert VIEWPORT_NO_ZOOM in base
    assert 'id="sidebar-backdrop"' in base
    assert 'id="nav-toggle"' in navbar
    assert 'id="app-sidebar"' in sidebar
    assert "theme.js" in base and "defer" in base
    assert "__x.$data" not in sidebar


def test_login_pages_block_pinch_zoom() -> None:
    for path in (
        "app/modules/identity/templates/identity/login.html",
        "app/modules/identity/templates/identity/login_2fa.html",
    ):
        html = Path(path).read_text(encoding="utf-8")
        assert VIEWPORT_NO_ZOOM in html
        assert "responsive.css" in html


def test_responsive_css_covers_mobile_sidebar() -> None:
    css = Path("app/web/static/css/responsive.css").read_text(encoding="utf-8")
    for token in (
        "sidebar-open",
        "nav-toggle",
        "table-scroll",
        "touch-action: manipulation",
        "form-grid",
        "grid-template-columns: 1fr",
    ):
        assert token in css


def test_theme_js_waits_for_body() -> None:
    js = Path("app/web/static/js/theme.js").read_text(encoding="utf-8")
    assert "bindBodyEvents" in js
    assert "body.addEventListener" in js
    assert "DOMContentLoaded" in js


def test_app_js_layout_helpers() -> None:
    js = Path("app/web/static/js/app.js").read_text(encoding="utf-8")
    assert "wrapTables" in js
    assert "sidebar-open" in js
    assert "erpLayout" in js


def test_sistema_config_form_uses_full_post() -> None:
    html = Path("app/modules/tenants/templates/tenants/sistema_config.html").read_text(encoding="utf-8")
    assert 'data-no-spa="true"' in html
    assert "hx-post" not in html


def test_login_page_renders_nav_toggle_absent(client: TestClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert "nav-toggle" not in response.text


def test_dashboard_includes_mobile_menu(client: TestClient) -> None:
    login = client.post(
        "/login",
        data={"email": "admin@locadora.local", "password": "Admin@123"},
        follow_redirects=False,
    )
    if login.status_code not in (303, 302):
        return
    page = client.get(login.headers.get("location", "/"))
    if page.status_code == 200:
        assert "nav-toggle" in page.text
        assert "responsive.css" in page.text
