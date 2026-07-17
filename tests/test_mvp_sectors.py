"""Testes dos setores MVP — papéis, menu e atalhos do dashboard."""

from __future__ import annotations

import uuid

import pytest

from app.core.rbac import SYSTEM_ROLE_TEMPLATES, expand_permissions
from app.modules.identity.service import AuthenticatedUser
from app.web.navigation import build_menu
from app.web.sectors import SECTORS, build_quick_links, resolve_primary_sector


def _user_from_template(slug: str) -> AuthenticatedUser:
    template = next(t for t in SYSTEM_ROLE_TEMPLATES if t.slug == slug)
    perms = expand_permissions(set(template.permissions))
    return AuthenticatedUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email=f"{slug}@test.com",
        full_name=slug.title(),
        is_active=True,
        is_superuser=False,
        roles=[slug],
        permissions=perms,
        filial_ids=[],
    )


@pytest.mark.parametrize(
    "slug",
    ["vendedor", "operador", "financeiro", "diretoria"],
)
def test_mvp_roles_exist(slug: str) -> None:
    slugs = {t.slug for t in SYSTEM_ROLE_TEMPLATES}
    assert slug in slugs


def test_vendedor_sees_reservas_not_fiscal() -> None:
    menu = build_menu(_user_from_template("vendedor"))
    labels = {s["label"] for s in menu}
    assert "Reservas" in labels
    assert "Comercial / CRM" in labels
    assert "Fiscal" not in labels
    assert "Financeiro" not in labels


def test_operador_sees_locacoes_not_comercial_crm_write() -> None:
    user = _user_from_template("operador")
    menu = build_menu(user)
    labels = {s["label"] for s in menu}
    assert "Locações" in labels
    assert "Reservas" in labels
    assert "Comercial / CRM" not in labels
    links = {lnk["label"] for lnk in build_quick_links(user)}
    assert "Novo Contrato" in links
    assert "Nova Proposta" not in links


def test_financeiro_sees_financeiro_fiscal_not_reservas_write() -> None:
    user = _user_from_template("financeiro")
    menu = build_menu(user)
    labels = {s["label"] for s in menu}
    assert "Financeiro" in labels
    assert "Fiscal" in labels
    assert "Reservas" not in labels
    assert "Locações" not in labels
    links = {lnk["label"] for lnk in build_quick_links(user)}
    assert "Contas a Receber" in links
    assert "Nova Reserva" not in links


def test_diretoria_read_only_menu() -> None:
    user = _user_from_template("diretoria")
    menu = build_menu(user)
    labels = {s["label"] for s in menu}
    assert "Relatórios" in labels
    assert "Cadastros" not in labels
    assert "Reservas" not in labels
    assert "Locações" not in labels
    config = next(s for s in menu if s["label"] == "Configurações")
    assert [c["label"] for c in config["children"]] == ["Autenticação 2FA"]
    sector = resolve_primary_sector(user)
    assert sector.slug == "diretoria"


def test_resolve_primary_sector_priority() -> None:
    user = AuthenticatedUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="multi@test.com",
        full_name="Multi",
        is_active=True,
        is_superuser=False,
        roles=["vendedor", "financeiro"],
        permissions=set(),
        filial_ids=[],
    )
    assert resolve_primary_sector(user).slug == "financeiro"


def test_all_mvp_sectors_defined() -> None:
    for slug in ("vendedor", "operador", "financeiro", "diretoria", "admin-empresa"):
        assert slug in SECTORS
