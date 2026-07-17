"""Testes da Fase 4 — repeater tarifário e rotas."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.main import app
from app.modules.tarifario.web import _parse_tabela_itens


def test_parse_tabela_itens_aligns_rows() -> None:
    cat = str(uuid.uuid4())
    itens = _parse_tabela_itens(
        [cat, ""],
        ["100", "50"],
        ["90"],
        ["80"],
        ["70"],
        ["600"],
        ["1", "0"],
    )
    assert len(itens) == 1
    assert itens[0].categoria_id == uuid.UUID(cat)
    assert itens[0].valor_1_3 == Decimal("100")
    assert itens[0].valor_4_7 == Decimal("90")
    assert itens[0].valor_mensal == Decimal("600")
    assert itens[0].km_livre is True


def test_tarifario_lote_route_registered() -> None:
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/tarifario/tabelas/{tabela_id}/itens/lote" in paths


def test_form_repeater_script_in_base() -> None:
    from pathlib import Path

    base = Path("app/web/templates/base.html").read_text(encoding="utf-8")
    assert "form-repeater.js" in base
