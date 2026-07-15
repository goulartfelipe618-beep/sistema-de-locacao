"""API REST do módulo de Cadastros."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

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
from app.modules.cadastros.schemas_extra import (
    FornecedorCreate,
    FornecedorRead,
    FornecedorUpdate,
    MotoristaCreate,
    MotoristaRead,
    MotoristaUpdate,
    ParceiroCreate,
    ParceiroRead,
    ParceiroUpdate,
    VendedorCreate,
    VendedorRead,
    VendedorUpdate,
)
from app.modules.cadastros.service import ClienteService, TabelaAuxiliarService
from app.modules.cadastros.service_extra import (
    FornecedorService,
    MotoristaService,
    ParceiroService,
    VendedorService,
)
from app.modules.identity.service import AuthenticatedUser

router = APIRouter(prefix="/cadastros", tags=["Cadastros"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


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


# ---- Motoristas ----
@router.get("/motoristas", response_model=dict)
async def api_list_motoristas(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.motorista.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    result = await MotoristaService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, MotoristaRead)


@router.post("/motoristas", response_model=MotoristaRead, status_code=status.HTTP_201_CREATED)
async def api_create_motorista(
    payload: MotoristaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.motorista.criar"))
    ],
) -> MotoristaRead:
    item = await MotoristaService(session).create(current_user.tenant_id, payload)
    return MotoristaRead.model_validate(item)


@router.get("/motoristas/{item_id}", response_model=MotoristaRead)
async def api_get_motorista(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.motorista.visualizar"))],
) -> MotoristaRead:
    return MotoristaRead.model_validate(await MotoristaService(session).get(item_id))


@router.patch("/motoristas/{item_id}", response_model=MotoristaRead)
async def api_update_motorista(
    item_id: uuid.UUID,
    payload: MotoristaUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.motorista.editar"))],
) -> MotoristaRead:
    return MotoristaRead.model_validate(await MotoristaService(session).update(item_id, payload))


# ---- Parceiros ----
@router.get("/parceiros", response_model=dict)
async def api_list_parceiros(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.parceiro.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    result = await ParceiroService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, ParceiroRead)


@router.post("/parceiros", response_model=ParceiroRead, status_code=status.HTTP_201_CREATED)
async def api_create_parceiro(
    payload: ParceiroCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.parceiro.criar"))
    ],
) -> ParceiroRead:
    return ParceiroRead.model_validate(
        await ParceiroService(session).create(current_user.tenant_id, payload)
    )


@router.get("/parceiros/{item_id}", response_model=ParceiroRead)
async def api_get_parceiro(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.parceiro.visualizar"))],
) -> ParceiroRead:
    return ParceiroRead.model_validate(await ParceiroService(session).get(item_id))


@router.patch("/parceiros/{item_id}", response_model=ParceiroRead)
async def api_update_parceiro(
    item_id: uuid.UUID,
    payload: ParceiroUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.parceiro.editar"))],
) -> ParceiroRead:
    return ParceiroRead.model_validate(await ParceiroService(session).update(item_id, payload))


# ---- Fornecedores ----
@router.get("/fornecedores", response_model=dict)
async def api_list_fornecedores(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.fornecedor.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    result = await FornecedorService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, FornecedorRead)


@router.post("/fornecedores", response_model=FornecedorRead, status_code=status.HTTP_201_CREATED)
async def api_create_fornecedor(
    payload: FornecedorCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.fornecedor.criar"))
    ],
) -> FornecedorRead:
    return FornecedorRead.model_validate(
        await FornecedorService(session).create(current_user.tenant_id, payload)
    )


@router.get("/fornecedores/{item_id}", response_model=FornecedorRead)
async def api_get_fornecedor(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.fornecedor.visualizar"))
    ],
) -> FornecedorRead:
    return FornecedorRead.model_validate(await FornecedorService(session).get(item_id))


@router.patch("/fornecedores/{item_id}", response_model=FornecedorRead)
async def api_update_fornecedor(
    item_id: uuid.UUID,
    payload: FornecedorUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.fornecedor.editar"))],
) -> FornecedorRead:
    return FornecedorRead.model_validate(await FornecedorService(session).update(item_id, payload))


# ---- Vendedores ----
@router.get("/vendedores", response_model=dict)
async def api_list_vendedores(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.vendedor.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    result = await VendedorService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, VendedorRead)


@router.post("/vendedores", response_model=VendedorRead, status_code=status.HTTP_201_CREATED)
async def api_create_vendedor(
    payload: VendedorCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("cadastros.vendedor.criar"))
    ],
) -> VendedorRead:
    return VendedorRead.model_validate(
        await VendedorService(session).create(current_user.tenant_id, payload)
    )


@router.get("/vendedores/{item_id}", response_model=VendedorRead)
async def api_get_vendedor(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.vendedor.visualizar"))],
) -> VendedorRead:
    return VendedorRead.model_validate(await VendedorService(session).get(item_id))


@router.patch("/vendedores/{item_id}", response_model=VendedorRead)
async def api_update_vendedor(
    item_id: uuid.UUID,
    payload: VendedorUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.vendedor.editar"))],
) -> VendedorRead:
    return VendedorRead.model_validate(await VendedorService(session).update(item_id, payload))
