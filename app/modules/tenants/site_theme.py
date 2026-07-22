"""Paleta do site público (white-label) — derivada das cores configuradas no ERP."""

from __future__ import annotations

from typing import Any

from app.modules.tenants.models import Tenant

DEFAULT_SITE_PRIMARY = "#111111"
DEFAULT_SITE_BACKGROUND = "#ffffff"
DEFAULT_SITE_TEXT = "#111111"

# Campos opcionais no tenant (nullable = usa derivado ou padrão)
SITE_THEME_COLOR_FIELDS: tuple[str, ...] = (
    "site_primary_color",
    "site_background_color",
    "site_text_color",
    "site_header_bg_color",
    "site_header_text_color",
    "site_topbar_bg_color",
    "site_topbar_tab_bg_color",
    "site_topbar_tab_text_color",
    "site_topbar_tab_active_bg_color",
    "site_topbar_tab_active_text_color",
    "site_button_bg_color",
    "site_button_text_color",
    "site_link_color",
    "site_border_color",
    "site_surface_color",
    "site_text_muted_color",
    "site_footer_bg_color",
    "site_footer_text_color",
)


def _expand_hex(color: str) -> str:
    color = color.strip()
    if len(color) == 4 and color.startswith("#"):
        return "#" + "".join(ch * 2 for ch in color[1:])
    return color


def _parse_hex(color: str) -> tuple[int, int, int]:
    hex_color = _expand_hex(color).lstrip("#")
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def _mix(color_a: str, color_b: str, weight_b: float) -> str:
    r1, g1, b1 = _parse_hex(color_a)
    r2, g2, b2 = _parse_hex(color_b)
    w = max(0.0, min(1.0, weight_b))
    return _rgb_to_hex(
        round(r1 * (1 - w) + r2 * w),
        round(g1 * (1 - w) + g2 * w),
        round(b1 * (1 - w) + b2 * w),
    )


def _relative_luminance(hex_color: str) -> float:
    def channel(value: int) -> float:
        c = value / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _parse_hex(hex_color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _on_color(background: str) -> str:
    return "#ffffff" if _relative_luminance(background) < 0.45 else "#111111"


def _primary_hover(primary: str) -> str:
    if _relative_luminance(primary) < 0.45:
        return _mix(primary, "#ffffff", 0.22)
    return _mix(primary, "#000000", 0.18)


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _parse_hex(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _tenant_color(tenant: Tenant, field: str) -> str | None:
    return getattr(tenant, field, None)


def resolved_site_colors(tenant: Tenant) -> dict[str, str]:
    """Cores efetivas do site (customizadas ou derivadas)."""
    primary = _tenant_color(tenant, "site_primary_color") or DEFAULT_SITE_PRIMARY
    bg = _tenant_color(tenant, "site_background_color") or DEFAULT_SITE_BACKGROUND
    text = _tenant_color(tenant, "site_text_color") or DEFAULT_SITE_TEXT

    header_bg = _tenant_color(tenant, "site_header_bg_color") or primary
    header_text = _tenant_color(tenant, "site_header_text_color") or _on_color(header_bg)
    topbar_bg = _tenant_color(tenant, "site_topbar_bg_color") or bg
    topbar_tab_bg = _tenant_color(tenant, "site_topbar_tab_bg_color") or _mix(bg, text, 0.22)
    topbar_tab_text = _tenant_color(tenant, "site_topbar_tab_text_color") or _mix(text, bg, 0.35)
    topbar_tab_active_bg = _tenant_color(tenant, "site_topbar_tab_active_bg_color") or primary
    topbar_tab_active_text = (
        _tenant_color(tenant, "site_topbar_tab_active_text_color") or _on_color(topbar_tab_active_bg)
    )
    button_bg = _tenant_color(tenant, "site_button_bg_color") or primary
    button_text = _tenant_color(tenant, "site_button_text_color") or _on_color(button_bg)
    link = _tenant_color(tenant, "site_link_color") or primary
    border = _tenant_color(tenant, "site_border_color") or _mix(text, bg, 0.12)
    surface = _tenant_color(tenant, "site_surface_color") or _mix(bg, text, 0.04)
    text_muted = _tenant_color(tenant, "site_text_muted_color") or _mix(text, bg, 0.35)
    text_soft = _mix(text, bg, 0.55)
    footer_bg = _tenant_color(tenant, "site_footer_bg_color") or primary
    footer_text = _tenant_color(tenant, "site_footer_text_color") or _on_color(footer_bg)

    return {
        "primary": primary,
        "background": bg,
        "text": text,
        "header_bg": header_bg,
        "header_text": header_text,
        "topbar_bg": topbar_bg,
        "topbar_tab_bg": topbar_tab_bg,
        "topbar_tab_text": topbar_tab_text,
        "topbar_tab_active_bg": topbar_tab_active_bg,
        "topbar_tab_active_text": topbar_tab_active_text,
        "button_bg": button_bg,
        "button_text": button_text,
        "link": link,
        "border": border,
        "surface": surface,
        "text_muted": text_muted,
        "text_soft": text_soft,
        "footer_bg": footer_bg,
        "footer_text": footer_text,
        "primary_hover": _primary_hover(button_bg),
        "on_primary": _on_color(primary),
    }


def site_theme_is_customized(tenant: Tenant) -> bool:
    return any(_tenant_color(tenant, field) for field in SITE_THEME_COLOR_FIELDS)


def site_theme_payload(tenant: Tenant) -> dict[str, Any]:
    """Payload para API pública / aplicação de CSS no site."""
    c = resolved_site_colors(tenant)
    pr, pg, pb = _parse_hex(c["primary"])

    css = {
        "--color-primary": c["primary"],
        "--color-primary-hover": c["primary_hover"],
        "--color-on-primary": c["on_primary"],
        "--color-bg": c["background"],
        "--color-bg-muted": c["surface"],
        "--color-text": c["text"],
        "--color-text-muted": c["text_muted"],
        "--color-text-soft": c["text_soft"],
        "--color-border": c["border"],
        "--color-overlay": _rgba(c["primary"], 0.55),
        "--color-header-bg": c["header_bg"],
        "--color-header-text": c["header_text"],
        "--color-topbar-bg": c["topbar_bg"],
        "--color-topbar-tab-bg": c["topbar_tab_bg"],
        "--color-topbar-tab-text": c["topbar_tab_text"],
        "--color-topbar-tab-active-bg": c["topbar_tab_active_bg"],
        "--color-topbar-tab-active-text": c["topbar_tab_active_text"],
        "--color-button-bg": c["button_bg"],
        "--color-button-text": c["button_text"],
        "--color-button-hover": _primary_hover(c["button_bg"]),
        "--color-link": c["link"],
        "--color-footer-bg": c["footer_bg"],
        "--color-footer-text": c["footer_text"],
        "--color-footer-link": _mix(c["footer_text"], c["footer_bg"], 0.25),
        "--color-surface": c["surface"],
    }

    return {
        "cores": {
            "primaria": c["primary"],
            "fundo": c["background"],
            "texto": c["text"],
            "cabecalho_fundo": c["header_bg"],
            "cabecalho_texto": c["header_text"],
            "topbar_fundo": c["topbar_bg"],
            "topbar_aba_fundo": c["topbar_tab_bg"],
            "topbar_aba_texto": c["topbar_tab_text"],
            "topbar_aba_ativa_fundo": c["topbar_tab_active_bg"],
            "topbar_aba_ativa_texto": c["topbar_tab_active_text"],
            "botao_fundo": c["button_bg"],
            "botao_texto": c["button_text"],
            "link": c["link"],
            "borda": c["border"],
            "superficie": c["surface"],
            "texto_secundario": c["text_muted"],
            "rodape_fundo": c["footer_bg"],
            "rodape_texto": c["footer_text"],
        },
        "css": css,
        "customizado": site_theme_is_customized(tenant),
    }
