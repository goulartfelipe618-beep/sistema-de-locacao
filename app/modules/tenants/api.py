"""Rotas da API REST do módulo de Empresas/Filiais (JSON)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PagedResponse, PageMeta, PageParams
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.schemas import (
    FilialCreate,
    FilialRead,
    FilialUpdate,
    TenantRead,
    TenantUpdate,
)
from app.modules.tenants.service import FilialService, TenantService

router = APIRouter()

ViewCompanyDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.empresa.visualizar"))
]
EditCompanyDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.empresa.editar"))
]
ViewFilialDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.filial.visualizar"))
]
CreateFilialDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.filial.criar"))
]
EditFilialDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.filial.editar"))
]
DeleteFilialDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.filial.excluir"))
]


# ------------------------------------------------------------------ Empresa
@router.get("/company", response_model=TenantRead, tags=["Empresa"])
async def get_company(
    session: ApiSessionDep,
    current_user: ViewCompanyDep,
) -> TenantRead:
    """Retorna os dados da empresa (tenant) do contexto atual."""
    tenant = await TenantService(session).get_tenant(current_user.tenant_id)
    return TenantRead.model_validate(tenant)


@router.put("/company", response_model=TenantRead, tags=["Empresa"])
async def update_company(
    payload: TenantUpdate,
    session: ApiSessionDep,
    current_user: EditCompanyDep,
) -> TenantRead:
    """Atualiza os dados cadastrais da empresa."""
    tenant = await TenantService(session).update_tenant(current_user.tenant_id, payload)
    return TenantRead.model_validate(tenant)


# ------------------------------------------------------------------ Filiais
@router.get("/branches", response_model=PagedResponse[FilialRead], tags=["Filiais"])
async def list_branches(
    session: ApiSessionDep,
    _user: ViewFilialDep,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=200),
) -> PagedResponse[FilialRead]:
    """Lista filiais paginadas do tenant atual."""
    result = await FilialService(session).list_filiais(PageParams(page=page, size=size))
    return PagedResponse[FilialRead](
        data=[FilialRead.model_validate(f) for f in result.items],
        meta=PageMeta(page=result.page, size=result.size, total=result.total, pages=result.pages),
    )


@router.get("/branches/{filial_id}", response_model=FilialRead, tags=["Filiais"])
async def get_branch(
    filial_id: uuid.UUID,
    session: ApiSessionDep,
    _user: ViewFilialDep,
) -> FilialRead:
    """Retorna uma filial pelo ID."""
    filial = await FilialService(session).get_filial(filial_id)
    return FilialRead.model_validate(filial)


@router.post(
    "/branches",
    response_model=FilialRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Filiais"],
)
async def create_branch(
    payload: FilialCreate,
    session: ApiSessionDep,
    current_user: CreateFilialDep,
) -> FilialRead:
    """Cria uma nova filial no tenant atual."""
    filial = await FilialService(session).create_filial(payload, tenant_id=current_user.tenant_id)
    await session.flush()
    return FilialRead.model_validate(filial)


@router.put("/branches/{filial_id}", response_model=FilialRead, tags=["Filiais"])
async def update_branch(
    filial_id: uuid.UUID,
    payload: FilialUpdate,
    session: ApiSessionDep,
    _user: EditFilialDep,
) -> FilialRead:
    """Atualiza uma filial existente."""
    filial = await FilialService(session).update_filial(filial_id, payload)
    return FilialRead.model_validate(filial)


@router.delete(
    "/branches/{filial_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["Filiais"],
)
async def delete_branch(
    filial_id: uuid.UUID,
    session: ApiSessionDep,
    _user: DeleteFilialDep,
) -> Response:
    """Remove (soft delete) uma filial."""
    await FilialService(session).delete_filial(filial_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
