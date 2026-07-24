"""Testes da paleta de cores do site público."""

from __future__ import annotations

from app.modules.tenants.models import Tenant
from app.modules.tenants.site_theme import resolved_site_colors, site_theme_payload


def test_site_theme_defaults_preto_branco() -> None:
    tenant = Tenant(slug="matriz", legal_name="Teste", plan="standard")
    payload = site_theme_payload(tenant)
    assert payload["customizado"] is False
    assert payload["css"]["--color-primary"] == "#111111"
    assert payload["css"]["--color-bg"] == "#ffffff"
    assert payload["css"]["--color-text"] == "#111111"
    assert payload["css"]["--color-on-primary"] == "#ffffff"
    assert payload["css"]["--color-header-bg"] == "#111111"
    assert payload["css"]["--color-button-bg"] == "#111111"
    assert payload["css"]["--color-footer-bg"] == "#111111"


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
    assert payload["css"]["--color-header-bg"] == "#1e5a8a"
    assert payload["css"]["--color-button-bg"] == "#1e5a8a"


def test_site_theme_extended_overrides() -> None:
    tenant = Tenant(
        slug="matriz",
        legal_name="Teste",
        plan="standard",
        site_primary_color="#111111",
        site_header_bg_color="#003366",
        site_header_text_color="#ffffff",
        site_button_bg_color="#ff6600",
        site_button_text_color="#ffffff",
        site_footer_bg_color="#222222",
        site_footer_text_color="#eeeeee",
        site_link_color="#0066cc",
    )
    colors = resolved_site_colors(tenant)
    payload = site_theme_payload(tenant)
    assert colors["header_bg"] == "#003366"
    assert colors["button_bg"] == "#ff6600"
    assert colors["footer_bg"] == "#222222"
    assert colors["link"] == "#0066cc"
    assert payload["css"]["--color-header-bg"] == "#003366"
    assert payload["css"]["--color-button-bg"] == "#ff6600"
    assert payload["css"]["--color-link"] == "#0066cc"
    assert payload["css"]["--color-footer-bg"] == "#222222"
    assert "--color-topbar-tab-bg" in payload["css"]
    assert "--color-topbar-tab-active-bg" in payload["css"]


def test_site_transition_defaults_disabled() -> None:
    tenant = Tenant(slug="matriz", legal_name="Teste", plan="standard")
    from app.modules.tenants.site_transition import site_transition_payload

    payload = site_transition_payload(tenant)
    assert payload["ativo"] is False
    assert payload["tamanho_px"] == 120
    assert payload["imagem_url"] is None


def test_site_transition_custom() -> None:
    tenant = Tenant(
        slug="matriz",
        legal_name="Teste",
        plan="standard",
        site_transition_enabled=True,
        site_transition_bg_color="#ffeedd",
        site_transition_image_size_px=180,
        site_transition_image_url="data:image/png;base64,abc",
    )
    from app.modules.tenants.site_transition import site_transition_payload

    payload = site_theme_payload(tenant)
    assert payload["transicao"]["ativo"] is True
    assert payload["transicao"]["fundo"] == "#ffeedd"
    assert payload["transicao"]["tamanho_px"] == 180
    assert payload["transicao"]["imagem_url"] == "data:image/png;base64,abc"


def test_site_showcase_defaults_empty() -> None:
    tenant = Tenant(slug="matriz", legal_name="Teste", plan="standard")
    from app.modules.tenants.site_showcase import site_showcase_payload

    payload = site_showcase_payload(tenant)
    assert len(payload["imagens"]) == 3
    assert all(row["imagem_url"] is None for row in payload["imagens"])
    assert payload["imagens"][0]["largura_px"] == 1080
    assert payload["imagens"][0]["altura_px"] == 1350


def test_site_showcase_custom() -> None:
    tenant = Tenant(
        slug="matriz",
        legal_name="Teste",
        plan="standard",
        site_showcase_1_url="data:image/jpeg;base64,abc",
        site_showcase_2_url="data:image/jpeg;base64,def",
        site_showcase_1_titulo="Agências",
        site_showcase_1_descricao="Encontre a unidade mais próxima.",
        site_showcase_1_cta_texto="Ver agências",
        site_showcase_1_cta_url="https://example.com/agencias",
        site_showcase_1_cta_target="_blank",
    )
    from app.modules.tenants.site_showcase import site_showcase_payload

    payload = site_theme_payload(tenant)
    assert payload["vitrine"]["imagens"][0]["imagem_url"] == "data:image/jpeg;base64,abc"
    assert payload["vitrine"]["imagens"][1]["imagem_url"] == "data:image/jpeg;base64,def"
    assert payload["vitrine"]["imagens"][2]["imagem_url"] is None
    assert payload["vitrine"]["imagens"][0]["titulo"] == "Agências"
    assert payload["vitrine"]["imagens"][0]["descricao"] == "Encontre a unidade mais próxima."
    assert payload["vitrine"]["imagens"][0]["cta_texto"] == "Ver agências"
    assert payload["vitrine"]["imagens"][0]["cta_url"] == "https://example.com/agencias"
    assert payload["vitrine"]["imagens"][0]["cta_target"] == "_blank"
    assert payload["vitrine"]["imagens"][0]["cta_nova_aba"] is True
    showcase = site_showcase_payload(tenant)
    assert showcase["imagens"][0]["cta_target"] == "_blank"


def test_site_theme_topbar_tab_colors() -> None:
    tenant = Tenant(
        slug="matriz",
        legal_name="Teste",
        plan="standard",
        site_topbar_tab_bg_color="#cccccc",
        site_topbar_tab_text_color="#444444",
        site_topbar_tab_active_bg_color="#ff6600",
        site_topbar_tab_active_text_color="#ffffff",
    )
    payload = site_theme_payload(tenant)
    assert payload["css"]["--color-topbar-tab-bg"] == "#cccccc"
    assert payload["css"]["--color-topbar-tab-text"] == "#444444"
    assert payload["css"]["--color-topbar-tab-active-bg"] == "#ff6600"
    assert payload["css"]["--color-topbar-tab-active-text"] == "#ffffff"
