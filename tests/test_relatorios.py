"""Testes do módulo Relatórios (§11): catálogo, engine, RBAC e menu."""

from __future__ import annotations

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.relatorios.catalog import REPORT_CATALOG, list_by_categoria
from app.modules.relatorios.engine import render_csv, render_xlsx, sha256_bytes
from app.shared.enums import RelCategoria, RelEmissaoStatus
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

REL_PERMS = {
    "dashboard.painel.visualizar",
    "relatorios.frota.visualizar",
    "relatorios.frota.exportar",
    "relatorios.locacao.visualizar",
    "relatorios.financeiro.visualizar",
    "relatorios.fiscal.visualizar",
    "relatorios.gerencial.visualizar",
    "relatorios.historico.visualizar",
    "relatorios.agendamento.visualizar",
}


def test_catalogo_tem_29_relatorios() -> None:
    assert len(REPORT_CATALOG) == 29


def test_catalogo_categorias() -> None:
    for cat in RelCategoria:
        items = list_by_categoria(cat)
        assert items, f"categoria {cat.value} vazia"
        assert all(r.categoria == cat for r in items)


def test_permissoes_relatorios_registradas() -> None:
    for code in (
        "relatorios.frota.visualizar",
        "relatorios.frota.exportar",
        "relatorios.historico.visualizar",
        "relatorios.agendamento.criar",
    ):
        assert code in PERMISSIONS_BY_CODE


def test_menu_relatorios_completo() -> None:
    menu = build_menu(_make_user(REL_PERMS))
    rel = next(s for s in menu if s["label"] == "Relatórios")
    labels = {item["label"] for item in rel["children"]}
    assert labels >= {"Frota", "Locação", "Financeiro", "Fiscal", "Gerencial", "Histórico", "Agendamentos"}
    assert all(item["enabled"] for item in rel["children"] if item["label"] in {"Frota", "Histórico"})


def test_engine_csv_xlsx() -> None:
    cols = ["a", "b"]
    rows = [[1, 2], [3, None]]
    csv_blob = render_csv(cols, rows)
    assert csv_blob.startswith(b"\xef\xbb\xbf")
    assert b"a,b" in csv_blob
    xlsx_blob = render_xlsx(cols, rows)
    assert xlsx_blob[:2] == b"PK"


def test_sha256_bytes() -> None:
    h = sha256_bytes(b"teste")
    assert len(h) == 64


def test_status_emissao_enum() -> None:
    assert RelEmissaoStatus.PENDENTE.value == "pendente"
    assert RelEmissaoStatus.CONCLUIDO.value == "concluido"
