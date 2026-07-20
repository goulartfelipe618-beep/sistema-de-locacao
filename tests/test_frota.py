"""Testes unitários do módulo Frota (schemas, máquina de estados, menu)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.modules.frota.schemas import DocumentoCreate, VeiculoCreate
from app.modules.frota.service import VEICULO_TRANSITIONS, _derive_documento_status
from app.shared.enums import DocumentoVeiculoStatus, DocumentoVeiculoTipo, VeiculoStatus
from app.web.navigation import build_menu
from tests.test_navigation import _make_user


def test_placa_normalizada() -> None:
    data = VeiculoCreate(
        placa="abc1d23",
        ano_fabricacao=2022,
        ano_modelo=2023,
        marca_id="00000000-0000-0000-0000-000000000002",
        modelo_id="00000000-0000-0000-0000-000000000003",
        combustivel_id="00000000-0000-0000-0000-000000000004",
    )
    assert data.placa == "ABC1D23"
    assert data.categoria_id is None


def test_placa_invalida() -> None:
    with pytest.raises(ValidationError):
        VeiculoCreate(
            placa="XX",
            ano_fabricacao=2022,
            ano_modelo=2023,
            marca_id="00000000-0000-0000-0000-000000000002",
            modelo_id="00000000-0000-0000-0000-000000000003",
            combustivel_id="00000000-0000-0000-0000-000000000004",
        )


def test_placa_formato_antigo_com_letras() -> None:
    data = VeiculoCreate(
        placa="abc-1234",
        ano_fabricacao=2020,
        ano_modelo=2020,
        marca_id="00000000-0000-0000-0000-000000000002",
        modelo_id="00000000-0000-0000-0000-000000000003",
        combustivel_id="00000000-0000-0000-0000-000000000004",
    )
    assert data.placa == "ABC1234"


def test_veiculo_dossie_route_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/frota/veiculos/{veiculo_id}" in paths


def test_veiculo_dossier_module_exports_builder() -> None:
    from app.modules.frota.dossier_veiculo import VeiculoDossier, build_veiculo_dossier

    assert callable(build_veiculo_dossier)
    assert VeiculoDossier.__dataclass_fields__["veiculo"]


def test_documento_requer_validade() -> None:
    with pytest.raises(ValidationError):
        DocumentoCreate(
            veiculo_id="00000000-0000-0000-0000-000000000001",
            tipo=DocumentoVeiculoTipo.CRLV,
        )


def test_derive_documento_status() -> None:
    assert _derive_documento_status(date.today() - timedelta(days=1)) == DocumentoVeiculoStatus.VENCIDO
    assert _derive_documento_status(date.today() + timedelta(days=10)) == DocumentoVeiculoStatus.A_VENCER
    assert _derive_documento_status(date.today() + timedelta(days=60)) == DocumentoVeiculoStatus.REGULAR


def test_veiculo_transitions_baixado_terminal() -> None:
    assert VEICULO_TRANSITIONS[VeiculoStatus.BAIXADO] == set()
    assert VeiculoStatus.BLOQUEADO in VEICULO_TRANSITIONS[VeiculoStatus.DISPONIVEL]
    assert VeiculoStatus.RESTRITO in VEICULO_TRANSITIONS[VeiculoStatus.DISPONIVEL]


def test_menu_frota_habilitado() -> None:
    perms = {
        "frota.veiculo.visualizar",
        "frota.categoria.visualizar",
        "frota.marca.visualizar",
        "frota.modelo.visualizar",
        "frota.combustivel.visualizar",
        "frota.acessorio.visualizar",
        "frota.documentacao.visualizar",
        "frota.telemetria.visualizar",
    }
    menu = build_menu(_make_user(perms))
    frota = next(s for s in menu if s["label"] == "Frota")
    by_label = {i["label"]: i for i in frota["children"]}
    for label, url in (
        ("Veículos", "/frota/veiculos"),
        ("Categorias", "/frota/categorias"),
        ("Marcas", "/frota/marcas"),
        ("Modelos", "/frota/modelos"),
        ("Combustíveis", "/frota/combustiveis"),
        ("Acessórios", "/frota/acessorios"),
        ("Documentação", "/frota/documentacao"),
        ("Telemetria", "/frota/telemetria"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url
