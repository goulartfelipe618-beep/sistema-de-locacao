"""Preferência de tema da interface (claro / escuro / intermediário)."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

THEME_COOKIE = "erp-ui-theme"
VALID_UI_THEMES = frozenset({"light", "dark", "hybrid"})
DEFAULT_UI_THEME = "hybrid"


def normalize_ui_theme(value: str | None) -> str:
    if value and value in VALID_UI_THEMES:
        return value
    return DEFAULT_UI_THEME


def read_ui_theme(request: Request) -> str:
    """Lê tema preferido: cookie persistente → sessão → padrão."""
    cookie = request.cookies.get(THEME_COOKIE)
    if cookie:
        return normalize_ui_theme(cookie)
    session_val = request.session.get(THEME_COOKIE)
    if session_val:
        return normalize_ui_theme(str(session_val))
    return DEFAULT_UI_THEME


def persist_ui_theme(response: Response, request: Request, theme: str) -> str:
    """Grava tema em cookie (1 ano) e sessão; retorna valor normalizado."""
    normalized = normalize_ui_theme(theme)
    request.session[THEME_COOKIE] = normalized
    response.set_cookie(
        key=THEME_COOKIE,
        value=normalized,
        max_age=60 * 60 * 24 * 365,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return normalized
