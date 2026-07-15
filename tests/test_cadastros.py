"""Testes unitários do módulo de Cadastros (schemas / regras locais)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.cadastros.schemas import ClienteCreate
from app.modules.cadastros.schemas_extra import MotoristaCreate, ParceiroCreate, VendedorCreate
from app.shared.enums import MotoristaVinculo, PersonType
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


def test_motorista_cliente_requires_cliente_id() -> None:
    with pytest.raises(ValidationError):
        MotoristaCreate(nome="Motorista X", vinculo=MotoristaVinculo.CLIENTE)


def test_parceiro_pf_requires_cpf() -> None:
    with pytest.raises(ValidationError):
        ParceiroCreate(person_type=PersonType.NATURAL, nome="Parceiro X")


def test_vendedor_create_defaults() -> None:
    vendedor = VendedorCreate(nome="Vendedor Y")
    assert vendedor.meta_contratos_mes == 0


def test_menu_clientes_enabled_with_permission() -> None:
    menu = build_menu(_make_user({"cadastros.cliente.visualizar"}))
    cadastros = next(s for s in menu if s["label"] == "Cadastros")
    clientes = next(i for i in cadastros["children"] if i["label"] == "Clientes")
    assert clientes["enabled"] is True
    assert clientes["url"] == "/cadastros/clientes"


def test_menu_cadastros_extras_enabled() -> None:
    perms = {
        "cadastros.motorista.visualizar",
        "cadastros.parceiro.visualizar",
        "cadastros.fornecedor.visualizar",
        "cadastros.vendedor.visualizar",
    }
    menu = build_menu(_make_user(perms))
    cadastros = next(s for s in menu if s["label"] == "Cadastros")
    by_label = {i["label"]: i for i in cadastros["children"]}
    for label, url in (
        ("Motoristas", "/cadastros/motoristas"),
        ("Parceiros", "/cadastros/parceiros"),
        ("Fornecedores", "/cadastros/fornecedores"),
        ("Vendedores", "/cadastros/vendedores"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url
