"""Middlewares HTTP transversais.

O :class:`RequestContextMiddleware` é o coração da observabilidade e do
multiempresa por requisição: gera o ``correlation_id``, popula o contexto de
execução (tenant/filial/usuário) a partir da sessão autenticada e registra
métricas básicas de cada requisição.
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core import context
from app.core.logging import get_logger

logger = get_logger("app.request")

CORRELATION_HEADER = "X-Correlation-ID"


def _parse_uuid(value: object) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Estabelece o contexto de execução e registra cada requisição.

    Deve ser adicionado *depois* do ``SessionMiddleware`` para que
    ``request.session`` já esteja disponível.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        context.reset_context()

        correlation_id = request.headers.get(CORRELATION_HEADER) or uuid.uuid4().hex
        context.set_correlation_id(correlation_id)

        # Popula o contexto multiempresa a partir da sessão autenticada (Web).
        session = request.scope.get("session") or {}
        context.set_tenant_id(_parse_uuid(session.get("tenant_id")))
        context.set_filial_id(_parse_uuid(session.get("filial_id")))
        context.set_user_id(_parse_uuid(session.get("user_id")))
        context.set_is_superuser(bool(session.get("is_superuser", False)))

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "Requisição falhou",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers[CORRELATION_HEADER] = correlation_id
        logger.info(
            "Requisição concluída",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
            },
        )
        return response
