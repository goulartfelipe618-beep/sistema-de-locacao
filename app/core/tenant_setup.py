"""Middleware que exige onboarding de configurações do sistema."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.modules.tenants.setup import (
    is_setup_exempt_path,
    refresh_tenant_session_from_db,
    resolve_setup_redirect,
)


class TenantSetupMiddleware(BaseHTTPMiddleware):
    """Redireciona usuários autenticados enquanto o tenant não concluiu setup."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        session = request.scope.get("session") or {}
        user_id = session.get("user_id")
        path = request.url.path

        if user_id:
            await refresh_tenant_session_from_db(request)
            session = request.scope.get("session") or {}

        if user_id and not is_setup_exempt_path(path):
            redirect = resolve_setup_redirect(session)
            if redirect and not path.startswith(redirect):
                return RedirectResponse(url=redirect, status_code=303)

        response = await call_next(request)
        return response
