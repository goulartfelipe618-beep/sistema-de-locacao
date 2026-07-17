"""Testes da Fase 5 — fiscal IBGE, integrações, automações e parâmetros."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.main import app
from app.modules.fiscal.web import _parse_aliquotas
from app.modules.integracoes.web import API_PUBLIC_SCOPES
from app.shared.enums import ImpostoTipo


def test_fase5_routes_registered() -> None:
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/cadastros/clientes/{cliente_id}/resumo" in paths
    assert "/fiscal/impostos/{config_id}/aliquotas/lote" in paths
    assert "/integracoes/configs/{config_id}/testar" in paths


def test_parse_aliquotas_batch() -> None:
    config_id = uuid.uuid4()
    items = _parse_aliquotas(
        config_id,
        ["iss"],
        ["5"],
        ["ISS serviços"],
        ["1401"],
        ["2026-01-01"],
        ["1"],
    )
    assert len(items) == 1
    assert items[0].config_id == config_id
    assert items[0].tipo == ImpostoTipo.ISS
    assert items[0].retencao is True
    assert items[0].vigencia_inicio == date(2026, 1, 1)


def test_api_public_scopes_defined() -> None:
    assert len(API_PUBLIC_SCOPES) >= 3
    ids = {s[0] for s in API_PUBLIC_SCOPES}
    assert "disponibilidade:read" in ids
    assert "reservas:write" in ids


def test_fase5_scripts_in_base() -> None:
    from pathlib import Path

    base = Path("app/web/templates/base.html").read_text(encoding="utf-8")
    for script in ("form-upload.js", "form-automation.js", "form-integracao.js"):
        assert script in base


def test_nfse_template_ibge_municipio() -> None:
    from pathlib import Path

    html = Path("app/modules/fiscal/templates/fiscal/nfse_form.html").read_text(encoding="utf-8")
    assert "data-ibge-municipio" in html
    assert "municipio_ibge" in html


def test_parametros_grouped_fieldsets() -> None:
    from pathlib import Path

    html = Path("app/modules/parametros/templates/parametros/list.html").read_text(encoding="utf-8")
    assert "param-category-panel" in html
    assert "grouped.items()" in html
