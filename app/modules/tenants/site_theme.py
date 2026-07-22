"""Paleta do site público (white-label) — derivada das cores configuradas no ERP."""

from __future__ import annotations

from typing import Any

from app.modules.tenants.models import Tenant

# Padrão atual do site institucional (preto e branco)
DEFAULT_SITE_PRIMARY = "#111111"
DEFAULT_SITE_BACKGROUND = "#ffffff"
DEFAULT_SITE_TEXT = "#111111"


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


def resolved_site_colors(tenant: Tenant) -> dict[str, str]:
    """Cores efetivas do site (customizadas ou padrão B&W)."""
    return {
        "primary": tenant.site_primary_color or DEFAULT_SITE_PRIMARY,
        "background": tenant.site_background_color or DEFAULT_SITE_BACKGROUND,
        "text": tenant.site_text_color or DEFAULT_SITE_TEXT,
    }


def site_theme_payload(tenant: Tenant) -> dict[str, Any]:
    """Payload para API pública / aplicação de CSS no site."""
    colors = resolved_site_colors(tenant)
    primary = colors["primary"]
    bg = colors["background"]
    text = colors["text"]
    primary_hover = _primary_hover(primary)
    on_primary = _on_color(primary)
    bg_muted = _mix(bg, text, 0.04)
    text_muted = _mix(text, bg, 0.35)
    text_soft = _mix(text, bg, 0.55)
    border = _mix(text, bg, 0.12)
    pr, pg, pb = _parse_hex(primary)

    css = {
        "--color-primary": primary,
        "--color-primary-hover": primary_hover,
        "--color-on-primary": on_primary,
        "--color-bg": bg,
        "--color-bg-muted": bg_muted,
        "--color-text": text,
        "--color-text-muted": text_muted,
        "--color-text-soft": text_soft,
        "--color-border": border,
        "--color-overlay": f"rgba({pr}, {pg}, {pb}, 0.55)",
    }

    return {
        "cores": {
            "primaria": primary,
            "fundo": bg,
            "texto": text,
        },
        "css": css,
        "customizado": any(
            (
                tenant.site_primary_color,
                tenant.site_background_color,
                tenant.site_text_color,
            )
        ),
    }
