"""Testes da lógica pura de RBAC."""

from __future__ import annotations

from app.core.rbac import SYSTEM_PERMISSIONS, expand_permissions, has_permission


def test_superuser_has_everything() -> None:
    assert has_permission(set(), "financeiro.caixa.editar", is_superuser=True) is True


def test_exact_match() -> None:
    perms = {"configuracoes.filial.visualizar"}
    assert has_permission(perms, "configuracoes.filial.visualizar") is True
    assert has_permission(perms, "configuracoes.filial.editar") is False


def test_module_wildcard() -> None:
    perms = {"financeiro.*"}
    assert has_permission(perms, "financeiro.caixa.editar") is True
    assert has_permission(perms, "frota.veiculo.editar") is False


def test_global_wildcard() -> None:
    perms = {"*"}
    assert has_permission(perms, "qualquer.coisa.aqui") is True


def test_expand_permissions_global() -> None:
    expanded = expand_permissions({"*"})
    assert len(expanded) == len(SYSTEM_PERMISSIONS)
    assert "dashboard.painel.visualizar" in expanded
