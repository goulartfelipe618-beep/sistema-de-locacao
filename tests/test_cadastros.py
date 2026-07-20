"""Testes unitários do módulo de Cadastros (schemas / regras locais)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.core.exceptions import ValidationError as AppValidationError
from app.modules.cadastros.schemas import ClienteCreate
from app.modules.cadastros.schemas_extra import MotoristaCreate, ParceiroCreate, VendedorCreate
from app.modules.cadastros.service import ClienteService
from app.shared.enums import ClienteStatus, MotoristaVinculo, PersonType
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


def test_cliente_desbloquear_rejects_active() -> None:
    cliente = MagicMock()
    cliente.status = ClienteStatus.ACTIVE
    cliente.blacklist = False

    svc = ClienteService(MagicMock())
    svc.get = AsyncMock(return_value=cliente)

    import asyncio

    with pytest.raises(AppValidationError, match="não está bloqueado"):
        asyncio.run(svc.desbloquear(uuid.uuid4()))


def test_parceiro_dossier_module_exports_builder() -> None:
    from app.modules.cadastros.dossier_parceiro import ParceiroDossier, build_parceiro_dossier

    assert callable(build_parceiro_dossier)
    assert ParceiroDossier.__dataclass_fields__["parceiro"]


def test_fornecedor_dossie_route_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/cadastros/fornecedores/{item_id}" in paths


def test_fornecedor_dossier_module_exports_builder() -> None:
    from app.modules.cadastros.dossier_fornecedor import FornecedorDossier, build_fornecedor_dossier

    assert callable(build_fornecedor_dossier)
    assert FornecedorDossier.__dataclass_fields__["fornecedor"]


def test_parceiro_dossie_route_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/cadastros/parceiros/{item_id}" in paths


def test_menu_cadastros_extras_enabled() -> None:
    perms = {
        "cadastros.parceiro.visualizar",
        "cadastros.fornecedor.visualizar",
        "cadastros.vendedor.visualizar",
    }
    menu = build_menu(_make_user(perms))
    cadastros = next(s for s in menu if s["label"] == "Cadastros")
    by_label = {i["label"]: i for i in cadastros["children"]}
    assert "Motoristas" not in by_label
    for label, url in (
        ("Parceiros", "/cadastros/parceiros"),
        ("Fornecedores", "/cadastros/fornecedores"),
        ("Vendedores", "/cadastros/vendedores"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url
