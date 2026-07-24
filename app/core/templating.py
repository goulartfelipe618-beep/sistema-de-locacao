"""Configuração do motor de templates Jinja2 (renderização no servidor).

Monta um ambiente Jinja2 com:
    * *Search paths* automáticos: o diretório de layout global (``app/web/templates``)
      e o diretório ``templates`` de cada módulo (organização feature-first).
    * Globais e filtros úteis (formatação de data/moeda, verificação de permissão).
    * Auto-escape de HTML (proteção contra XSS).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse
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
    _register_instruction_macros(env)
    return env


def _register_instruction_macros(env: Environment) -> None:
    """Expõe macros de instruções globalmente (evita 500 se faltar {% from %})."""
    try:
        mod = env.get_template("macros/form_instructions.html").module
    except Exception:
        return
    for name in ("form_instructions", "list_create_actions", "form_page_header"):
        macro = getattr(mod, name, None)
        if macro is not None:
            env.globals[name] = macro


# Objeto de templates compartilhado (Starlette gerencia o ``request`` no contexto).
templates = Jinja2Templates(env=_build_environment())

_APP_CONTENT_RE = re.compile(
    r'(<main[^>]*\bid=["\']app-content["\'][^>]*>.*?</main>)',
    re.DOTALL | re.IGNORECASE,
)


def extract_app_content(html: str) -> str | None:
    """Extrai o fragmento ``#app-content`` de uma página HTML completa."""
    match = _APP_CONTENT_RE.search(html)
    return match.group(1) if match else None


def is_spa_request(request: Request) -> bool:
    """True quando a navegação SPA pede só o fragmento #app-content."""
    return request.headers.get("X-ERP-SPA") == "1"


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
    from app.web.navigation import build_menu, resolve_active_menu_url

    ctx: dict[str, Any] = dict(context or {})
    from app import __version__

    ctx.setdefault("static_version", __version__)
    current_user = getattr(request.state, "current_user", None)
    ctx.setdefault("current_user", current_user)
    ctx.setdefault("current_path", request.url.path)
    branding = getattr(request.state, "tenant_branding", None) or request.session.get("tenant_branding")
    ctx.setdefault("tenant_branding", branding)
    fiscal_on = bool((branding or {}).get("fiscal_emissao_habilitada"))
    menu = build_menu(current_user, fiscal_emissao_habilitada=fiscal_on)
    ctx.setdefault("menu", menu)
    ctx.setdefault("active_menu_url", resolve_active_menu_url(request.url.path, menu))
    ctx.setdefault("csrf_token", ensure_csrf_token(request))
    ctx.setdefault(
        "notificacoes_nao_lidas",
        getattr(request.state, "notificacoes_nao_lidas", 0),
    )
    display_name = (branding or {}).get("display_name")
    ctx["app_name"] = display_name if display_name else settings.app_name
    ctx.setdefault("ui_theme", read_ui_theme(request))
    flash = request.session.pop("_flash", None)
    ctx.setdefault("flash", flash)
    if is_spa_request(request):
        html = templates.env.get_template(template_name).render({"request": request, **ctx})
        fragment = extract_app_content(html)
        if fragment:
            return HTMLResponse(fragment, status_code=status_code)
    return templates.TemplateResponse(request, template_name, ctx, status_code=status_code)
