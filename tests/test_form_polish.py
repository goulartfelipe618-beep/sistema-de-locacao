"""Testes da Fase 6 — polimento UX, acessibilidade e catálogo de ajuda."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FORM_ENGINE = Path("app/web/static/js/form-engine.js").read_text(encoding="utf-8")
FORM_DIR = Path("app/modules")

CRITICAL_FORM_PATHS = [
    "cadastros/templates/cadastros/cliente_form.html",
    "locacoes/templates/locacoes/contrato_form.html",
    "locacoes/templates/locacoes/checkout_form.html",
    "locacoes/templates/locacoes/checkin_form.html",
    "financeiro/templates/financeiro/receber_form.html",
    "fiscal/templates/fiscal/nfse_form.html",
    "fiscal/templates/fiscal/nfe_form.html",
    "comercial/templates/comercial/proposta_form.html",
    "tarifario/templates/tarifario/tabela_form.html",
]


def test_fase6_form_engine_a11y_helpers() -> None:
    for symbol in (
        "FIELD_HELP",
        "injectFieldHelp",
        "setupA11y",
        "setupDirtyCancel",
        "ensureFormLegend",
        "syncAriaDescribedBy",
    ):
        assert symbol in FORM_ENGINE


def test_fase6_field_help_catalog_covers_common_fields() -> None:
    required_keys = (
        "cpf",
        "cnpj",
        "cep",
        "placa",
        "municipio_ibge",
        "vencimento",
        "cliente_id",
        "veiculo_id",
        "justificativa",
    )
    for key in required_keys:
        assert f"{key}:" in FORM_ENGINE or f'"{key}"' in FORM_ENGINE


def test_fase6_login_page_a11y(client: TestClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    html = response.text
    assert 'id="login-title"' in html
    assert 'for="email"' in html
    assert 'for="password"' in html
    assert 'class="form-help"' in html
    assert "form-legend-required" in html
    assert 'aria-describedby="help-email"' in html


def test_fase6_form_engine_loaded_in_base() -> None:
    base = Path("app/web/templates/base.html").read_text(encoding="utf-8")
    assert "form-engine.js" in base


@pytest.mark.parametrize("rel_path", CRITICAL_FORM_PATHS)
def test_fase6_critical_forms_have_post_and_csrf(rel_path: str) -> None:
    html = (FORM_DIR / rel_path).read_text(encoding="utf-8")
    assert 'method="post"' in html.lower()
    assert "csrf_token" in html or 'extends "base.html"' in html


def test_fase6_module_forms_use_post_or_base_csrf() -> None:
    """Formulários POST devem ter CSRF explícito ou herdar injeção via base.html + app.js."""
    forms = list(FORM_DIR.rglob("*_form.html"))
    assert len(forms) >= 40
    missing: list[str] = []
    for path in forms:
        text = path.read_text(encoding="utf-8")
        if 'method="post"' not in text.lower():
            continue
        if "csrf_token" not in text and 'extends "base.html"' not in text:
            missing.append(str(path))
    assert not missing, f"Forms POST sem CSRF nem base: {missing[:5]}"


def test_fase6_focus_visible_css() -> None:
    css = Path("app/web/static/css/app.css").read_text(encoding="utf-8")
    assert ":focus-visible" in css


def test_fase6_form_help_macro_available() -> None:
    macros = Path("app/web/templates/macros/forms.html").read_text(encoding="utf-8")
    assert "field_help" in macros
    assert "form_legend" in macros


def test_fase6_e2e_playwright_config_exists() -> None:
    config = Path("e2e/playwright.config.ts")
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert "webServer" in text
    assert Path("e2e/tests/login.spec.ts").is_file()
    assert Path("e2e/tests/critical-forms.spec.ts").is_file()
