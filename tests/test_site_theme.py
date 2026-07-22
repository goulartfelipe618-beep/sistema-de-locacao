"""Testes da paleta de cores do site público."""

from __future__ import annotations

from app.modules.tenants.models import Tenant
from app.modules.tenants.site_theme import site_theme_payload


def test_site_theme_defaults_preto_branco() -> None:
    tenant = Tenant(slug="matriz", legal_name="Teste", plan="standard")
    payload = site_theme_payload(tenant)
    assert payload["customizado"] is False
    assert payload["css"]["--color-primary"] == "#111111"
    assert payload["css"]["--color-bg"] == "#ffffff"
    assert payload["css"]["--color-text"] == "#111111"
    assert payload["css"]["--color-on-primary"] == "#ffffff"


def test_site_theme_custom_colors() -> None:
    tenant = Tenant(
        slug="matriz",
        legal_name="Teste",
        plan="standard",
        site_primary_color="#1e5a8a",
        site_background_color="#f0f4f8",
        site_text_color="#0a1628",
    )
    payload = site_theme_payload(tenant)
    assert payload["customizado"] is True
    assert payload["css"]["--color-primary"] == "#1e5a8a"
    assert payload["css"]["--color-bg"] == "#f0f4f8"
    assert payload["css"]["--color-text"] == "#0a1628"
    assert payload["cores"]["primaria"] == "#1e5a8a"
