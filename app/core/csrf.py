"""Proteção CSRF para mutações do painel administrativo (cookie session).

A API REST (``/api/*``) não usa cookies de sessão e fica fora do escopo.
O token vive na sessão do servidor e é exigido via header ``X-CSRF-Token``
ou campo de formulário ``csrf_token``.

Implementado como middleware ASGI puro (sem ``BaseHTTPMiddleware``) para
poder reler o body do formulário sem quebrar ``Form()`` do FastAPI
(antes: POST /login → 422).
"""

from __future__ import annotations

import secrets
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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


def _token_from_urlencoded(body: bytes) -> str | None:
    try:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return None
    values = parsed.get(CSRF_FORM_FIELD)
    if not values:
        return None
    return values[0]


def _token_from_multipart(body: bytes, content_type: str) -> str | None:
    marker = "boundary="
    if marker not in content_type:
        return None
    boundary = content_type.split(marker, 1)[1].strip()
    if boundary.startswith('"') and boundary.endswith('"'):
        boundary = boundary[1:-1]
    if not boundary:
        return None

    delimiter = b"--" + boundary.encode("ascii", errors="ignore")
    field_header = f'name="{CSRF_FORM_FIELD}"'.encode()
    for part in body.split(delimiter):
        if field_header not in part:
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end < 0:
            continue
        value = part[header_end + 4 :]
        if value.endswith(b"\r\n"):
            value = value[:-2]
        if value.endswith(b"--"):
            value = value[:-2]
        return value.decode("utf-8", errors="replace").strip()
    return None


def extract_csrf_from_body(body: bytes, content_type: str) -> str | None:
    """Extrai o token CSRF do body sem consumir o stream da request."""
    if "application/x-www-form-urlencoded" in content_type:
        return _token_from_urlencoded(body)
    if "multipart/form-data" in content_type:
        return _token_from_multipart(body, content_type)
    return None


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay_receive(body: bytes) -> Receive:
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


class CSRFMiddleware:
    """Valida token CSRF em requisições mutáveis do painel Web."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        if method in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        session = scope.get("session")
        if not isinstance(session, dict):
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        expected = session.get(CSRF_SESSION_KEY)
        provided: str | None = headers.get(CSRF_HEADER.lower())

        content_type = headers.get("content-type", "")
        body = b""
        if not provided and (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            body = await _read_body(receive)
            provided = extract_csrf_from_body(body, content_type)
            receive = _replay_receive(body)

        if (
            not expected
            or not provided
            or not secrets.compare_digest(str(provided), str(expected))
        ):
            logger.warning("CSRF rejeitado em %s %s", method, path)
            response = PlainTextResponse("CSRF token inválido ou ausente.", status_code=403)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
