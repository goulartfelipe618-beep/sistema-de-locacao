"""Rotas da API REST do módulo de Identidade (JSON).

Prontas para consumo futuro por site, aplicativos e parceiros. Toda a lógica
reside nos serviços; as rotas apenas orquestram entrada/saída.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.config import settings
from app.core.database import UnitOfWork
from app.core.deps import ApiSessionDep, get_current_api_user, require_api_permission
from app.core.exceptions import AuthenticationError, TenantResolutionError
from app.core.pagination import PagedResponse, PageMeta, PageParams
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.modules.identity.schemas import (
    CurrentUserRead,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.modules.identity.service import AuthenticatedUser, AuthService, UserService
from app.modules.tenants.repository import TenantRepository

router = APIRouter()

ViewUsersDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.usuario.visualizar"))
]
CreateUsersDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.usuario.criar"))
]


async def _resolve_tenant_id(request: Request) -> uuid.UUID:
    """Resolve o tenant do login por header/query, com fallback ao padrão.

    Multiempresa: em produção SaaS, virá do subdomínio. Nesta fase, aceita o
    header ``X-Tenant-Slug`` ou o query param ``tenant``; caso ausente, usa o
    tenant padrão configurado.
    """
    slug = (
        request.headers.get("X-Tenant-Slug")
        or request.query_params.get("tenant")
        or settings.default_tenant_slug
    )
    async with UnitOfWork(tenant_id=None) as uow:
        tenant = await TenantRepository(uow.session).get_by_slug(slug)
    if tenant is None:
        raise TenantResolutionError(f"Empresa (tenant) não encontrada: {slug}")
    return tenant.id


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _issue_token_pair(user_id: uuid.UUID, tenant_id: uuid.UUID, *, is_superuser: bool) -> TokenPair:
    """Emite o par access/refresh com claims coerentes e canônicos do banco."""
    claims = {"tenant_id": str(tenant_id), "is_superuser": is_superuser}
    refresh_claims = {"tenant_id": str(tenant_id), "is_superuser": is_superuser}
    return TokenPair(
        access_token=create_access_token(str(user_id), claims),
        refresh_token=create_refresh_token(str(user_id), refresh_claims),
    )


# ------------------------------------------------------------- Autenticação
@router.post("/auth/login", response_model=TokenPair, tags=["Autenticação"])
async def login(payload: LoginRequest, request: Request) -> TokenPair:
    """Autentica e emite o par de tokens (access + refresh)."""
    tenant_id = await _resolve_tenant_id(request)
    user = await AuthService().authenticate(
        tenant_id=tenant_id,
        email=payload.email,
        password=payload.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return _issue_token_pair(user.id, user.tenant_id, is_superuser=user.is_superuser)


@router.post("/auth/refresh", response_model=TokenPair, tags=["Autenticação"])
async def refresh_token(payload: RefreshRequest) -> TokenPair:
    """Renova tokens após validar no banco que o usuário ainda está ativo.

    Não confia em ``is_superuser`` do JWT antigo: os claims são rederivados
    do registro atual do usuário.
    """
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    try:
        user_id = uuid.UUID(str(claims["sub"]))
        tenant_id = uuid.UUID(str(claims["tenant_id"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Refresh token malformado.", code="token_invalid") from exc

    async with UnitOfWork(tenant_id=tenant_id) as uow:
        from app.modules.identity.repository import UserRepository

        user = await UserRepository(uow.session).get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError(
                "Usuário inválido ou inativo.",
                code="invalid_user",
            )
        return _issue_token_pair(user.id, user.tenant_id, is_superuser=user.is_superuser)


@router.get("/auth/me", response_model=CurrentUserRead, tags=["Autenticação"])
async def read_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> CurrentUserRead:
    """Retorna o usuário autenticado com papéis e permissões resolvidos."""
    return CurrentUserRead(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=current_user.roles,
        permissions=sorted(current_user.permissions),
    )


# -------------------------------------------------------------------- Usuários
@router.get("/users", response_model=PagedResponse[UserRead], tags=["Usuários"])
async def list_users(
    session: ApiSessionDep,
    _user: ViewUsersDep,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=200),
    search: str | None = Query(None),
) -> PagedResponse[UserRead]:
    """Lista usuários paginados do tenant atual."""
    result = await UserService(session).list_users(PageParams(page=page, size=size), search=search)
    return PagedResponse[UserRead](
        data=[UserRead.model_validate(u) for u in result.items],
        meta=PageMeta(page=result.page, size=result.size, total=result.total, pages=result.pages),
    )


@router.get("/users/{user_id}", response_model=UserRead, tags=["Usuários"])
async def get_user(
    user_id: uuid.UUID,
    session: ApiSessionDep,
    _user: ViewUsersDep,
) -> UserRead:
    """Retorna um usuário pelo ID."""
    user = await UserService(session).get_user(user_id)
    return UserRead.model_validate(user)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Usuários"],
)
async def create_user(
    payload: UserCreate,
    session: ApiSessionDep,
    current_user: CreateUsersDep,
) -> UserRead:
    """Cria um novo usuário no tenant atual."""
    user = await UserService(session).create_user(payload, tenant_id=current_user.tenant_id)
    await session.flush()
    return UserRead.model_validate(user)
