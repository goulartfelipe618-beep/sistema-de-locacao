"""Testes unitários do módulo de Cadastros (schemas / regras locais)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.cadastros.schemas import ClienteCreate
from app.shared.enums import PersonType
from app.web.navigation import build_menu
from tests.test_navigation import _make_user


def test_cliente_pf_requires_cpf() -> None:
    with pytest.raises(ValidationError):
        ClienteCreate(person_type=PersonType.NATURAL, nome="João Silva")


def test_cliente_pj_requires_cnpj() -> None:
    with pytest.raises(ValidationError):
        ClienteCreate(person_type=PersonType.LEGAL, nome="Empresa LTDA")


def test_cliente_pf_valid_cpf() -> None:
    # CPF válido de exemplo: 390.533.447-05
    cliente = ClienteCreate(
        person_type=PersonType.NATURAL,
        nome="João Silva",
        cpf="39053344705",
    )
    assert cliente.cpf == "39053344705"
    assert cliente.cnpj is None


def test_menu_clientes_enabled_with_permission() -> None:
    menu = build_menu(_make_user({"cadastros.cliente.visualizar"}))
    cadastros = next(s for s in menu if s["label"] == "Cadastros")
    clientes = next(i for i in cadastros["children"] if i["label"] == "Clientes")
    assert clientes["enabled"] is True
    assert clientes["url"] == "/cadastros/clientes"
