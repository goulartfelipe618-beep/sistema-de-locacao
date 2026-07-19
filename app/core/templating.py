"""Configuração do motor de templates Jinja2 (renderização no servidor).

Monta um ambiente Jinja2 com:
    * *Search paths* automáticos: o diretório de layout global (``app/web/templates``)
      e o diretório ``templates`` de cada módulo (organização feature-first).
    * Globais e filtros úteis (formatação de data/moeda, verificação de permissão).
    * Auto-escape de HTML (proteção contra XSS).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from app.core.config import settings

_APP_DIR = Path(__file__).resolve().parent.parent
_WEB_TEMPLATES = _APP_DIR / "web" / "templates"
_MODULES_DIR = _APP_DIR / "modules"


def _build_search_paths() -> list[str]:
    """Constrói a lista de diretórios de templates (layout + módulos)."""
    paths: list[str] = [str(_WEB_TEMPLATES)]
    for module_templates in sorted(_MODULES_DIR.glob("*/templates")):
        paths.append(str(module_templates))
    return paths


# ------------------------------------------------------------------- Filtros
def _format_datetime(value: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    return value.strftime(fmt) if value else "-"


def _format_date(value: date | None, fmt: str = "%d/%m/%Y") -> str:
    return value.strftime(fmt) if value else "-"


def _format_currency(value: Decimal | float | int | None) -> str:
    if value is None:
        return "R$ 0,00"
    inteiro = f"{Decimal(value):,.2f}"
    # Converte do padrão en-US (1,234.56) para pt-BR (1.234,56).
    inteiro = inteiro.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {inteiro}"


def _build_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_build_search_paths()),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
        auto_reload=not settings.is_production,
    )
    env.filters["datetime"] = _format_datetime
    env.filters["date"] = _format_date
    env.filters["currency"] = _format_currency
    from app.shared.value_objects import format_cnpj, format_cpf

    env.filters["cpf"] = format_cpf
    env.filters["cnpj"] = format_cnpj
    env.globals["app_name"] = settings.app_name
    env.globals["environment"] = settings.environment
    from app.web.form_instructions import get_form_instruction

    env.globals["form_instruction"] = get_form_instruction
    return env


# Objeto de templates compartilhado (Starlette gerencia o ``request`` no contexto).
templates = Jinja2Templates(env=_build_environment())


def render(
    request: Request,
    template_name: str,
    context: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
) -> Any:
    """Renderiza um template injetando o contexto comum de layout.

    O usuário atual (quando autenticado) é lido de ``request.state.current_user``
    e disponibilizado ao template junto da árvore de navegação já filtrada por
    permissões.
    """
    from app.core.csrf import ensure_csrf_token
    from app.core.ui_theme import read_ui_theme
    from app.web.navigation import build_menu

    ctx: dict[str, Any] = dict(context or {})
    current_user = getattr(request.state, "current_user", None)
    ctx.setdefault("current_user", current_user)
    ctx.setdefault("current_path", request.url.path)
    ctx.setdefault("menu", build_menu(current_user))
    ctx.setdefault("csrf_token", ensure_csrf_token(request))
    branding = getattr(request.state, "tenant_branding", None) or request.session.get("tenant_branding")
    ctx.setdefault("tenant_branding", branding)
    display_name = (branding or {}).get("display_name")
    ctx["app_name"] = display_name if display_name else settings.app_name
    ctx.setdefault("ui_theme", read_ui_theme(request))
    flash = request.session.pop("_flash", None)
    ctx.setdefault("flash", flash)
    return templates.TemplateResponse(request, template_name, ctx, status_code=status_code)
