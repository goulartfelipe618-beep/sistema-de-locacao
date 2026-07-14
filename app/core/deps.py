"""Dependências de injeção (composition layer) para rotas Web e API.

Aqui a infraestrutura (sessão, contexto, segurança) é conectada às regras de
identidade/RBAC. As rotas apenas declaram estas dependências; nenhuma regra de
negócio é escrita nas rotas.

Importante (API + RLS): a sessão de banco autenticada (``get_api_db_session``)
**depende** de :func:`get_current_api_user`, garantindo que o GUC
``app.current_tenant_id`` esteja definido **antes** da abertura da sessão da
requisição. Nunca declare ``get_db_session`` antes da autenticação JWT em rotas
protegidas da API.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core import context
from app.core.database import UnitOfWork, get_db_session
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.logging import get_logger
from app.core.rbac import has_permission
from app.core.security import decode_token
from app.modules.audit.service import audit_service
from app.modules.identity.service import AuthenticatedUser, RBACService
from app.shared.enums import AuditAction

logger = get_logger(__name__)

# Sessão Web: o tenant já vem do cookie via RequestContextMiddleware.
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

_bearer_scheme = HTTPBearer(auto_error=False, description="Token JWT de acesso")


# ==========================================================================
# WEB (sessão por cookie assinado)
# ==========================================================================
async def get_optional_web_user(
    request: Request,
    session: SessionDep,
) -> AuthenticatedUser | None:
    """Carrega o usuário autenticado da sessão (ou ``None`` se anônimo)."""
    user_id = context.get_user_id()
    if user_id is None:
        return None
    authenticated = await RBACService(session).load_by_id(user_id)
    request.state.current_user = authenticated
    return authenticated


async def require_web_user(
    request: Request,
    user: Annotated[AuthenticatedUser | None, Depends(get_optional_web_user)],
) -> AuthenticatedUser:
    """Exige um usuário autenticado; caso contrário, redireciona para o login."""
    if user is None:
        raise AuthenticationError("Autenticação necessária.", code="login_required")
    request.state.current_user = user
    return user


def require_web_permission(
    permission_code: str,
) -> Callable[..., Coroutine[Any, Any, AuthenticatedUser]]:
    """Fábrica de dependência que exige uma permissão específica (Web)."""

    async def _checker(
        user: Annotated[AuthenticatedUser, Depends(require_web_user)],
    ) -> AuthenticatedUser:
        if not has_permission(user.permissions, permission_code, is_superuser=user.is_superuser):
            await audit_service.record(
                AuditAction.ACCESS_DENIED,
                description=f"Acesso negado à permissão '{permission_code}'.",
            )
            raise PermissionDeniedError(
                "Você não tem permissão para acessar este recurso.",
                details={"required": permission_code},
            )
        return user

    return _checker


# ==========================================================================
# API REST (Bearer JWT)
# ==========================================================================
async def get_current_api_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthenticatedUser:
    """Autentica requisições de API via token Bearer e popula o contexto.

    Define o contexto de tenant/usuário **antes** do uso da sessão da requisição,
    garantindo a aplicação correta do Row-Level Security.
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Token de acesso ausente.", code="missing_token")

    payload = decode_token(credentials.credentials, expected_type="access")

    try:
        user_id = UUID(str(payload["sub"]))
        tenant_id = UUID(str(payload["tenant_id"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Token malformado.", code="token_invalid") from exc

    context.set_tenant_id(tenant_id)
    context.set_user_id(user_id)
    context.set_is_superuser(bool(payload.get("is_superuser", False)))

    async with UnitOfWork(tenant_id=tenant_id) as uow:
        authenticated = await RBACService(uow.session).load_by_id(user_id)

    if authenticated is None:
        raise AuthenticationError("Usuário inválido ou inativo.", code="invalid_user")

    # Alinha o GUC lógico ao valor canônico do banco (evita claims stale).
    context.set_is_superuser(authenticated.is_superuser)
    return authenticated


async def get_api_db_session(
    _user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> AsyncIterator[AsyncSession]:
    """Sessão de banco para rotas API autenticadas.

    Depende explicitamente de :func:`get_current_api_user` para que o tenant
    esteja no contexto **antes** de ``get_db_session`` aplicar o GUC de RLS.
    O FastAPI cacheia ``get_current_api_user`` na mesma requisição.
    """
    async for session in get_db_session():
        yield session


ApiSessionDep = Annotated[AsyncSession, Depends(get_api_db_session)]


def require_api_permission(
    permission_code: str,
) -> Callable[..., Coroutine[Any, Any, AuthenticatedUser]]:
    """Fábrica de dependência que exige uma permissão específica (API)."""

    async def _checker(
        user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
    ) -> AuthenticatedUser:
        if not has_permission(user.permissions, permission_code, is_superuser=user.is_superuser):
            await audit_service.record(
                AuditAction.ACCESS_DENIED,
                description=f"[API] Acesso negado à permissão '{permission_code}'.",
            )
            raise PermissionDeniedError(
                "Permissão insuficiente.",
                details={"required": permission_code},
            )
        return user

    return _checker
