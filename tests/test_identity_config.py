"""Testes de configuração de usuários e papéis (§14.3 / §14.4)."""

from __future__ import annotations

import uuid

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.identity.models import Permission
from app.modules.identity.schemas import RoleCreate, RoleUpdate
from app.modules.identity.service import group_permissions_by_module


def test_permissoes_identidade_registradas() -> None:
    for code in (
        "identidade.usuario.editar",
        "identidade.usuario.excluir",
        "identidade.papel.criar",
        "identidade.papel.editar",
        "identidade.papel.excluir",
    ):
        assert code in PERMISSIONS_BY_CODE


def test_role_create_slug_valido() -> None:
    role = RoleCreate(slug="atendente-n2", name="Atendente Nível 2")
    assert role.slug == "atendente-n2"


def test_role_update_campos_opcionais() -> None:
    data = RoleUpdate(name="Gerente", permission_ids=[])
    assert data.description is None
    assert data.permission_ids == []


def test_group_permissions_by_module() -> None:
    perms = [
        Permission(
            code="frota.veiculo.visualizar",
            module="frota",
            resource="veiculo",
            action="visualizar",
            description="Ver veículos",
        ),
        Permission(
            code="cadastros.cliente.visualizar",
            module="cadastros",
            resource="cliente",
            action="visualizar",
            description="Ver clientes",
        ),
        Permission(
            code="frota.veiculo.editar",
            module="frota",
            resource="veiculo",
            action="editar",
            description="Editar veículos",
        ),
    ]
    groups = group_permissions_by_module(perms)
    assert [g[0] for g in groups] == ["cadastros", "frota"]
    assert len(groups[1][1]) == 2
