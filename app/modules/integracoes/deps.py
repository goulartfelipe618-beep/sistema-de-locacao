"""Dependências de autenticação por API Key (§12.5)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context
from app.core.config import settings
from app.core.database import UnitOfWork, get_db_session
from app.core.exceptions import AuthenticationError, PermissionDeniedError, TenantResolutionError
from app.modules.integracoes.models import IntApiKey
from app.modules.integracoes.rate_limit import enforce_api_key_rate_limit
from app.modules.integracoes.service import ApiKeyService
from app.modules.tenants.repository import TenantRepository


async def _resolve_tenant_id(request: Request) -> UUID:
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


async def get_api_key_record(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> IntApiKey:
    if not x_api_key:
        raise AuthenticationError("API Key ausente.", code="missing_api_key")
    tenant_id = await _resolve_tenant_id(request)
    context.set_tenant_id(tenant_id)
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        item = await ApiKeyService(uow.session).authenticate(x_api_key)
    await enforce_api_key_rate_limit(item.key_prefix, item.rate_limit_por_minuto)
    return item


async def get_public_db_session(
    _key: Annotated[IntApiKey, Depends(get_api_key_record)],
) -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


PublicSessionDep = Annotated[AsyncSession, Depends(get_public_db_session)]


def require_api_key_scope(
    scope: str,
) -> Callable[..., Coroutine[Any, Any, IntApiKey]]:
    async def _checker(
        key: Annotated[IntApiKey, Depends(get_api_key_record)],
        session: PublicSessionDep,
    ) -> IntApiKey:
        if not ApiKeyService(session).has_scope(key, scope):
            raise PermissionDeniedError(
                "Escopo insuficiente para esta operação.",
                details={"required": scope},
            )
        return key

    return _checker
