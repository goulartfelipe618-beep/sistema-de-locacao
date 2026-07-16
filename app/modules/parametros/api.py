"""Rotas da API REST do módulo Parâmetros (§14.5)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.exceptions import NotFoundError
from app.modules.identity.service import AuthenticatedUser
from app.modules.parametros.schemas import ParametroBulkUpdate, ParametroUpdate, ParametroValorRead
from app.modules.parametros.service import ParametroService
from app.shared.enums import ParametroCategoria

router = APIRouter(prefix="/parametros", tags=["Parâmetros"])

ViewDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.parametro.visualizar"))
]
EditDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("configuracoes.parametro.editar"))
]


@router.get("", response_model=list[ParametroValorRead])
async def list_parametros(
    session: ApiSessionDep,
    current_user: ViewDep,
    filial_id: uuid.UUID | None = None,
    categoria: ParametroCategoria | None = None,
) -> list[ParametroValorRead]:
    return await ParametroService(session).list_resolved(
        current_user.tenant_id, filial_id=filial_id, categoria=categoria
    )


@router.post("/bulk", response_model=list[ParametroValorRead])
async def bulk_update_parametros(
    payload: ParametroBulkUpdate,
    session: ApiSessionDep,
    current_user: EditDep,
) -> list[ParametroValorRead]:
    return await ParametroService(session).bulk_update(
        payload.valores, current_user.tenant_id, filial_id=payload.filial_id
    )


@router.get("/{chave}", response_model=ParametroValorRead)
async def get_parametro(
    chave: str,
    session: ApiSessionDep,
    current_user: ViewDep,
    filial_id: uuid.UUID | None = None,
) -> ParametroValorRead:
    svc = ParametroService(session)
    items = await svc.list_resolved(current_user.tenant_id, filial_id=filial_id)
    for item in items:
        if item.chave == chave:
            return item
    svc.get_definition(chave)
    raise NotFoundError(f"Parâmetro não encontrado: {chave}")


@router.put("/{chave}", response_model=ParametroValorRead)
async def update_parametro(
    chave: str,
    payload: ParametroUpdate,
    session: ApiSessionDep,
    current_user: EditDep,
) -> ParametroValorRead:
    return await ParametroService(session).set_valor(
        chave, payload.valor, current_user.tenant_id, filial_id=payload.filial_id
    )


@router.delete("/{chave}", response_model=ParametroValorRead)
async def reset_parametro(
    chave: str,
    session: ApiSessionDep,
    current_user: EditDep,
    filial_id: uuid.UUID | None = Query(default=None),
) -> ParametroValorRead:
    return await ParametroService(session).reset_valor(
        chave, current_user.tenant_id, filial_id=filial_id
    )
