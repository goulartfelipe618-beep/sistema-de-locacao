"""Rotas da API REST do módulo de Identidade (JSON).

Prontas para consumo futuro por site, aplicativos e parceiros. Toda a lógica
reside nos serviços; as rotas apenas orquestram entrada/saída.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.config import settings
from app.core.database import UnitOfWork
from app.core.deps import ApiSessionDep, get_current_api_user, require_api_permission
from app.core.exceptions import AuthenticationError, TenantResolutionError
from app.core.pagination import PagedResponse, PageMeta, PageParams
from app.core.security import (
    create_2fa_pending_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.modules.identity.schemas import (
    AuthLoginResponse,
    CurrentUserRead,
    Login2FARequest,
    LoginRequest,
    RefreshRequest,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    TokenPair,
    TwoFactorConfirmRequest,
    TwoFactorDisableRequest,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.modules.identity.service import AuthenticatedUser, AuthService, RoleService, UserService
from app.modules.identity.twofa_service import TwoFactorService
from app.modules.identity.totp import decrypt_recovery_codes
from app.modules.tenants.repository import TenantRepository

router = APIRouter()

ViewUsersDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.usuario.visualizar"))
]
CreateUsersDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.usuario.criar"))
]
EditUsersDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.usuario.editar"))
]
ViewRolesDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.papel.visualizar"))
]
EditRolesDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.papel.editar"))
]
CreateRolesDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("identidade.papel.criar"))
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
@router.post("/auth/login", response_model=AuthLoginResponse, tags=["Autenticação"])
async def login(payload: LoginRequest, request: Request) -> AuthLoginResponse:
    """Autentica (1º fator). Se 2FA ativo, retorna ``pending_token`` em vez de JWT."""
    tenant_id = await _resolve_tenant_id(request)
    auth = AuthService()
    user = await auth.verify_credentials(
        tenant_id=tenant_id,
        email=payload.email,
        password=payload.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    if user.totp_enabled and user.totp_secret_encrypted:
        return AuthLoginResponse(
            requires_2fa=True,
            pending_token=create_2fa_pending_token(user.id, user.tenant_id),
        )
    await auth.finalize_login(
        user,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    pair = _issue_token_pair(user.id, user.tenant_id, is_superuser=user.is_superuser)
    return AuthLoginResponse(
        requires_2fa=False,
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/auth/login/2fa", response_model=TokenPair, tags=["Autenticação"])
async def login_2fa(payload: Login2FARequest, request: Request) -> TokenPair:
    """Conclui login com código TOTP ou recuperação."""
    claims = decode_token(payload.pending_token, expected_type="2fa_pending")
    user_id = uuid.UUID(str(claims["sub"]))
    tenant_id = uuid.UUID(str(claims["tenant_id"]))
    auth = AuthService()
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        user = await TwoFactorService(uow.session).verify_login(
            user_id,
            tenant_id,
            payload.code,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    await auth.finalize_login(
        user,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return _issue_token_pair(user.id, user.tenant_id, is_superuser=user.is_superuser)


@router.get("/auth/2fa/status", response_model=TwoFactorStatusResponse, tags=["Autenticação"])
async def twofa_status(
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> TwoFactorStatusResponse:
    """Status do 2FA do usuário autenticado."""
    user = await UserService(session).get_user(current_user.id)
    remaining = len(decrypt_recovery_codes(user.recovery_codes_encrypted))
    return TwoFactorStatusResponse(
        enabled=user.totp_enabled,
        enabled_at=user.totp_enabled_at,
        recovery_codes_remaining=remaining,
    )


@router.post("/auth/2fa/setup", response_model=TwoFactorSetupResponse, tags=["Autenticação"])
async def twofa_setup(
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> TwoFactorSetupResponse:
    """Inicia configuração 2FA (QR Code)."""
    data = await TwoFactorService(session).begin_setup(current_user.id)
    return TwoFactorSetupResponse(
        provisioning_uri=data.provisioning_uri,
        qr_data_uri=data.qr_data_uri,
    )


@router.post("/auth/2fa/confirm", tags=["Autenticação"])
async def twofa_confirm(
    payload: TwoFactorConfirmRequest,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> dict[str, list[str]]:
    """Confirma 2FA e retorna códigos de recuperação (única vez)."""
    codes = await TwoFactorService(session).confirm_setup(current_user.id, payload.code)
    return {"recovery_codes": codes}


@router.post("/auth/2fa/disable", status_code=status.HTTP_204_NO_CONTENT, tags=["Autenticação"])
async def twofa_disable(
    payload: TwoFactorDisableRequest,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> Response:
    """Desativa 2FA do usuário autenticado."""
    await TwoFactorService(session).disable(
        current_user.id,
        password=payload.password,
        code=payload.code,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> CurrentUserRead:
    """Retorna o usuário autenticado com papéis e permissões resolvidos."""
    user = await UserService(session).get_user(current_user.id)
    return CurrentUserRead(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=current_user.roles,
        permissions=sorted(current_user.permissions),
        totp_enabled=user.totp_enabled,
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


@router.patch("/users/{user_id}", response_model=UserRead, tags=["Usuários"])
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    session: ApiSessionDep,
    _user: EditUsersDep,
) -> UserRead:
    """Atualiza um usuário existente."""
    user = await UserService(session).update_user(user_id, payload)
    return UserRead.model_validate(user)


# -------------------------------------------------------------------- Papéis
@router.get("/roles", response_model=list[RoleRead], tags=["Papéis"])
async def list_roles(
    session: ApiSessionDep,
    _user: ViewRolesDep,
) -> list[RoleRead]:
    """Lista papéis do tenant."""
    from app.modules.identity.repository import RoleRepository

    roles = await RoleRepository(session).list_ordered()
    return [RoleRead.model_validate(r) for r in roles]


@router.post(
    "/roles",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Papéis"],
)
async def create_role(
    payload: RoleCreate,
    session: ApiSessionDep,
    current_user: CreateRolesDep,
) -> RoleRead:
    """Cria papel personalizado."""
    role = await RoleService(session).create_role(payload, tenant_id=current_user.tenant_id)
    return RoleRead.model_validate(role)


@router.patch("/roles/{role_id}", response_model=RoleRead, tags=["Papéis"])
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    session: ApiSessionDep,
    _user: EditRolesDep,
) -> RoleRead:
    """Atualiza papel e permissões."""
    role = await RoleService(session).update_role(role_id, payload)
    return RoleRead.model_validate(role)
