"""Testes dos endpoints JSON para combobox async."""

from __future__ import annotations

from app.main import app


def test_combobox_routes_registered() -> None:
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/cadastros/clientes/json" in paths
    assert "/cadastros/fornecedores/json" in paths
    assert "/frota/veiculos/json" in paths
    assert "/frota/modelos/json" in paths
