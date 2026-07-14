"""Proteção CSRF para mutações do painel administrativo (cookie session).

A API REST (``/api/*``) não usa cookies de sessão e fica fora do escopo.
O token vive na sessão do servidor e é exigido via header ``X-CSRF-Token``
ou campo de formulário ``csrf_token``.

A leitura de ``request.form()`` no middleware é segura: o Starlette/FastAPI
armazena o resultado em cache para as dependências ``Form()`` das rotas.
"""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from app.core.logging import get_logger

logger = get_logger(__name__)

CSRF_SESSION_KEY = "_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
EXEMPT_PREFIXES = ("/api/", "/static/")


def ensure_csrf_token(request: Request) -> str:
    """Garante um token CSRF na sessão e o retorna."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


class CSRFMiddleware(BaseHTTPMiddleware):
    """Valida token CSRF em requisições mutáveis do painel Web."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return await call_next(request)

        session = request.scope.get("session")
        if not isinstance(session, dict):
            return await call_next(request)

        expected = session.get(CSRF_SESSION_KEY)
        provided: str | None = request.headers.get(CSRF_HEADER)

        content_type = request.headers.get("content-type", "")
        if not provided and (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            form = await request.form()
            raw = form.get(CSRF_FORM_FIELD)
            provided = str(raw) if raw is not None else None

        if (
            not expected
            or not provided
            or not secrets.compare_digest(str(provided), str(expected))
        ):
            logger.warning("CSRF rejeitado em %s %s", request.method, path)
            return PlainTextResponse("CSRF token inválido ou ausente.", status_code=403)

        return await call_next(request)
