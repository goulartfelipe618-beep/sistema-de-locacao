"""Testes de slides do site (upload ERP + API pública)."""

from __future__ import annotations

import re

from app.core.rbac import PERMISSIONS_BY_CODE
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

# PNG 1×1 válido (sem dependência de Pillow)
_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

INT_SITE_PERMS = {
    "dashboard.painel.visualizar",
    "integracoes.site.visualizar",
    "integracoes.site.editar",
}


def _login_admin(client) -> None:
    login = client.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    client.post(
        "/login",
        data={"email": "admin@locadora.local", "password": "Admin@123", "csrf_token": m.group(1)},
        follow_redirects=True,
    )


def test_permissoes_site_slides_registradas() -> None:
    assert "integracoes.site.visualizar" in PERMISSIONS_BY_CODE
    assert "integracoes.site.editar" in PERMISSIONS_BY_CODE


def test_menu_site_slides() -> None:
    menu = build_menu(_make_user(INT_SITE_PERMS))
    section = next(s for s in menu if s["label"] == "Integrações")
    labels = {item["label"] for item in section["children"]}
    assert "Site — Slides" in labels


def test_site_slides_page_and_upload(client) -> None:
    _login_admin(client)
    page = client.get("/integracoes/site/slides")
    assert page.status_code == 200
    assert "Adicionar slide" in page.text

    m = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert m
    resp = client.post(
        "/integracoes/site/slides/novo",
        data={"csrf_token": m.group(1), "titulo": "Slide teste E2E"},
        files={"imagem": ("hero.png", _MIN_PNG, "image/png")},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    after = client.get("/integracoes/site/slides")
    assert after.status_code == 200
    assert "Slide teste E2E" in after.text
