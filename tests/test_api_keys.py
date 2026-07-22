"""Testes de exclusão de API Keys públicas."""

from __future__ import annotations

import re

from app.core.rbac import PERMISSIONS_BY_CODE

INT_API_PERMS = {
    "dashboard.painel.visualizar",
    "integracoes.api_publica.visualizar",
    "integracoes.api_publica.criar",
    "integracoes.api_publica.editar",
}


def _login_admin(client) -> None:
    login = client.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    client.post(
        "/login",
        data={"email": "admin@locadora.local", "password": "Admin@123", "csrf_token": m.group(1)},
        follow_redirects=True,
    )


def test_permissao_api_publica_editar_registrada() -> None:
    assert "integracoes.api_publica.editar" in PERMISSIONS_BY_CODE


def test_api_key_excluir_fluxo_confirmacao(client) -> None:
    _login_admin(client)

    page = client.get("/integracoes/api")
    assert page.status_code == 200
    m = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert m

    created = client.post(
        "/integracoes/api/keys/novo",
        data={
            "csrf_token": m.group(1),
            "nome": "Chave teste exclusão",
            "scopes": ["catalogo:read"],
        },
        follow_redirects=False,
    )
    assert created.status_code == 200
    assert "Chave teste exclusão" in created.text

    listing = client.get("/integracoes/api")
    assert "Chave teste exclusão" in listing.text
    link = re.search(
        r'href="/integracoes/api/keys/([0-9a-f-]{36})/excluir"[^>]*>Excluir</a>',
        listing.text,
    )
    assert link, "Botão Excluir deve aparecer na listagem"
    key_id = link.group(1)

    confirm = client.get(f"/integracoes/api/keys/{key_id}/excluir")
    assert confirm.status_code == 200
    assert "Tem certeza que deseja excluir esta chave?" in confirm.text
    assert "Chave teste exclusão" in confirm.text
    assert "Sim, excluir API Key" in confirm.text

    m2 = re.search(r'name="csrf_token" value="([^"]+)"', confirm.text)
    assert m2
    deleted = client.post(
        f"/integracoes/api/keys/{key_id}/excluir",
        data={"csrf_token": m2.group(1)},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert deleted.headers["location"] == "/integracoes/api"

    after = client.get("/integracoes/api")
    assert "Chave teste exclusão" not in after.text
