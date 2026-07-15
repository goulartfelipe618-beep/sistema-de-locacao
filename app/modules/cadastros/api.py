"""API REST do módulo de Cadastros."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.cadastros.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    TabelaAuxiliarCreate,
    TabelaAuxiliarRead,
)
from app.modules.cadastros.service import ClienteService, TabelaAuxiliarService
from app.modules.identity.service import AuthenticatedUser

router = APIRouter(prefix="/cadastros", tags=["Cadastros"])


@router.get("/clientes", response_model=dict)
async def api_list_clientes(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.cliente.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    """Lista clientes (JSON)."""
    result = await ClienteService(session).list_clientes(PageParams(page=page, size=size), search=q)
    return {
        "items": [ClienteRead.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


@router.post("/clientes", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def api_create_cliente(
    payload: ClienteCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.cliente.criar"))
    ],
) -> ClienteRead:
    """Cria cliente via API."""
    cliente = await ClienteService(session).create(current_user.tenant_id, payload)
    return ClienteRead.model_validate(cliente)


@router.get("/clientes/{cliente_id}", response_model=ClienteRead)
async def api_get_cliente(
    cliente_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.cliente.visualizar"))],
) -> ClienteRead:
    """Detalhe de cliente."""
    cliente = await ClienteService(session).get(cliente_id)
    return ClienteRead.model_validate(cliente)


@router.patch("/clientes/{cliente_id}", response_model=ClienteRead)
async def api_update_cliente(
    cliente_id: uuid.UUID,
    payload: ClienteUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.cliente.editar"))],
) -> ClienteRead:
    """Atualiza cliente."""
    cliente = await ClienteService(session).update(cliente_id, payload)
    return ClienteRead.model_validate(cliente)


@router.get("/tabelas/{grupo}", response_model=list[TabelaAuxiliarRead])
async def api_list_tabelas(
    grupo: str,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.tabela.visualizar"))
    ],
) -> list[TabelaAuxiliarRead]:
    """Lista itens auxiliares de um grupo."""
    await TabelaAuxiliarService(session).ensure_defaults(current_user.tenant_id)
    result = await TabelaAuxiliarService(session).list_by_grupo(
        grupo, PageParams(page=1, size=200), apenas_ativos=True
    )
    return [TabelaAuxiliarRead.model_validate(i) for i in result.items]


@router.post(
    "/tabelas",
    response_model=TabelaAuxiliarRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_create_tabela(
    payload: TabelaAuxiliarCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.tabela.criar"))
    ],
) -> TabelaAuxiliarRead:
    """Cria item auxiliar."""
    item = await TabelaAuxiliarService(session).create(current_user.tenant_id, payload)
    return TabelaAuxiliarRead.model_validate(item)
