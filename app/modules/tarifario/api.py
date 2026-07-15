"""API REST do módulo Tarifário."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.identity.service import AuthenticatedUser
from app.modules.tarifario.schemas import (
    CancelamentoSimulacao,
    CancelamentoSimulacaoRequest,
    PoliticaCreate,
    PoliticaFaixaCreate,
    PoliticaFaixaRead,
    PoliticaFaixaUpdate,
    PoliticaRead,
    PoliticaUpdate,
    PricingQuoteInput,
    PricingQuoteRequest,
    PricingQuoteResult,
    ProtecaoCategoriaLink,
    ProtecaoCategoriaRead,
    ProtecaoCreate,
    ProtecaoRead,
    ProtecaoUpdate,
    TabelaCreate,
    TabelaItemCreate,
    TabelaItemRead,
    TabelaItemUpdate,
    TabelaRead,
    TabelaUpdate,
    TaxaCreate,
    TaxaRead,
    TaxaUpdate,
    TemporadaCreate,
    TemporadaRead,
    TemporadaUpdate,
)
from app.modules.tarifario.service import (
    PoliticaCancelamentoService,
    PricingService,
    ProtecaoService,
    TabelaTarifaService,
    TaxaService,
    TemporadaService,
)
from app.shared.enums import CadastroStatus, TarifarioCanal, TaxaAplicacao

router = APIRouter(prefix="/tarifario", tags=["Tarifário"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


# ------------------------------------------------------------------ Tabelas
@router.get("/tabelas", response_model=dict)
async def api_list_tabelas(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    canal: TarifarioCanal | None = None,
    filial_id: uuid.UUID | None = None,
    status: CadastroStatus | None = None,
) -> dict:
    await PricingService(session).ensure_defaults(current_user.tenant_id)
    result = await TabelaTarifaService(session).list_items(
        PageParams(page=page, size=size),
        canal=canal,
        filial_id=filial_id,
        status=status,
        search=q,
    )
    return _page_dict(result, TabelaRead)


@router.post("/tabelas", response_model=TabelaRead, status_code=status.HTTP_201_CREATED)
async def api_create_tabela(
    payload: TabelaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.criar"))
    ],
) -> TabelaRead:
    item = await TabelaTarifaService(session).create(current_user.tenant_id, payload)
    return TabelaRead.model_validate(item)


@router.get("/tabelas/{item_id}", response_model=TabelaRead)
async def api_get_tabela(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.visualizar"))
    ],
) -> TabelaRead:
    return TabelaRead.model_validate(await TabelaTarifaService(session).get(item_id))


@router.patch("/tabelas/{item_id}", response_model=TabelaRead)
async def api_update_tabela(
    item_id: uuid.UUID,
    payload: TabelaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.editar"))
    ],
) -> TabelaRead:
    return TabelaRead.model_validate(
        await TabelaTarifaService(session).update(item_id, payload)
    )


@router.delete(
    "/tabelas/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_tabela(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.excluir"))
    ],
) -> Response:
    await TabelaTarifaService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tabelas/{item_id}/itens", response_model=dict)
async def api_list_tabela_itens(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.visualizar"))
    ],
) -> dict:
    items = await TabelaTarifaService(session).list_itens(item_id)
    return {"items": [TabelaItemRead.model_validate(i) for i in items]}


@router.post(
    "/tabelas/{item_id}/itens",
    response_model=TabelaItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_add_tabela_item(
    item_id: uuid.UUID,
    payload: TabelaItemCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.editar"))
    ],
) -> TabelaItemRead:
    item = await TabelaTarifaService(session).add_item(
        current_user.tenant_id, item_id, payload
    )
    return TabelaItemRead.model_validate(item)


@router.patch("/tabelas/{item_id}/itens/{tabela_item_id}", response_model=TabelaItemRead)
async def api_update_tabela_item(
    item_id: uuid.UUID,
    tabela_item_id: uuid.UUID,
    payload: TabelaItemUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.editar"))
    ],
) -> TabelaItemRead:
    item = await TabelaTarifaService(session).update_item(
        item_id, tabela_item_id, payload
    )
    return TabelaItemRead.model_validate(item)


@router.delete(
    "/tabelas/{item_id}/itens/{tabela_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_remove_tabela_item(
    item_id: uuid.UUID,
    tabela_item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.tabela.editar"))
    ],
) -> Response:
    await TabelaTarifaService(session).remove_item(item_id, tabela_item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------- Temporadas
@router.get("/temporadas", response_model=dict)
async def api_list_temporadas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.temporada.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    filial_id: uuid.UUID | None = None,
    categoria_id: uuid.UUID | None = None,
    status: CadastroStatus | None = None,
) -> dict:
    result = await TemporadaService(session).list_items(
        PageParams(page=page, size=size),
        filial_id=filial_id,
        categoria_id=categoria_id,
        status=status,
        search=q,
    )
    return _page_dict(result, TemporadaRead)


@router.post(
    "/temporadas",
    response_model=TemporadaRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_create_temporada(
    payload: TemporadaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.temporada.criar"))
    ],
) -> TemporadaRead:
    item = await TemporadaService(session).create(current_user.tenant_id, payload)
    return TemporadaRead.model_validate(item)


@router.get("/temporadas/{item_id}", response_model=TemporadaRead)
async def api_get_temporada(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.temporada.visualizar"))
    ],
) -> TemporadaRead:
    return TemporadaRead.model_validate(await TemporadaService(session).get(item_id))


@router.patch("/temporadas/{item_id}", response_model=TemporadaRead)
async def api_update_temporada(
    item_id: uuid.UUID,
    payload: TemporadaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.temporada.editar"))
    ],
) -> TemporadaRead:
    return TemporadaRead.model_validate(
        await TemporadaService(session).update(item_id, payload)
    )


@router.delete(
    "/temporadas/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_temporada(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.temporada.excluir"))
    ],
) -> Response:
    await TemporadaService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------- Taxas
@router.get("/taxas", response_model=dict)
async def api_list_taxas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.taxa.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    aplicacao: TaxaAplicacao | None = None,
    status: CadastroStatus | None = None,
) -> dict:
    result = await TaxaService(session).list_items(
        PageParams(page=page, size=size),
        aplicacao=aplicacao,
        status=status,
        search=q,
    )
    return _page_dict(result, TaxaRead)


@router.post("/taxas", response_model=TaxaRead, status_code=status.HTTP_201_CREATED)
async def api_create_taxa(
    payload: TaxaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.taxa.criar"))
    ],
) -> TaxaRead:
    item = await TaxaService(session).create(current_user.tenant_id, payload)
    return TaxaRead.model_validate(item)


@router.get("/taxas/{item_id}", response_model=TaxaRead)
async def api_get_taxa(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.taxa.visualizar"))
    ],
) -> TaxaRead:
    return TaxaRead.model_validate(await TaxaService(session).get(item_id))


@router.patch("/taxas/{item_id}", response_model=TaxaRead)
async def api_update_taxa(
    item_id: uuid.UUID,
    payload: TaxaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.taxa.editar"))
    ],
) -> TaxaRead:
    return TaxaRead.model_validate(await TaxaService(session).update(item_id, payload))


@router.delete(
    "/taxas/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_taxa(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.taxa.excluir"))
    ],
) -> Response:
    await TaxaService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------- Proteções
@router.get("/protecoes", response_model=dict)
async def api_list_protecoes(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.protecao.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: CadastroStatus | None = None,
) -> dict:
    result = await ProtecaoService(session).list_items(
        PageParams(page=page, size=size), status=status, search=q
    )
    return _page_dict(result, ProtecaoRead)


@router.post("/protecoes", response_model=ProtecaoRead, status_code=status.HTTP_201_CREATED)
async def api_create_protecao(
    payload: ProtecaoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.protecao.criar"))
    ],
) -> ProtecaoRead:
    item = await ProtecaoService(session).create(current_user.tenant_id, payload)
    return ProtecaoRead.model_validate(item)


@router.get("/protecoes/{item_id}", response_model=ProtecaoRead)
async def api_get_protecao(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.protecao.visualizar"))
    ],
) -> ProtecaoRead:
    return ProtecaoRead.model_validate(await ProtecaoService(session).get(item_id))


@router.patch("/protecoes/{item_id}", response_model=ProtecaoRead)
async def api_update_protecao(
    item_id: uuid.UUID,
    payload: ProtecaoUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.protecao.editar"))
    ],
) -> ProtecaoRead:
    return ProtecaoRead.model_validate(
        await ProtecaoService(session).update(item_id, payload)
    )


@router.delete(
    "/protecoes/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_protecao(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.protecao.excluir"))
    ],
) -> Response:
    await ProtecaoService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/protecoes/{item_id}/categorias", response_model=dict)
async def api_list_protecao_categorias(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.protecao.visualizar"))
    ],
) -> dict:
    items = await ProtecaoService(session).list_categorias(item_id)
    return {"items": [ProtecaoCategoriaRead.model_validate(i) for i in items]}


@router.post(
    "/protecoes/{item_id}/categorias",
    response_model=ProtecaoCategoriaRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_link_protecao_categoria(
    item_id: uuid.UUID,
    payload: ProtecaoCategoriaLink,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.protecao.editar"))
    ],
) -> ProtecaoCategoriaRead:
    item = await ProtecaoService(session).link_categoria(
        current_user.tenant_id, item_id, payload.categoria_id
    )
    return ProtecaoCategoriaRead.model_validate(item)


# ---------------------------------------------------------- Políticas Cancelamento
@router.get("/politicas", response_model=dict)
async def api_list_politicas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    canal: TarifarioCanal | None = None,
    status: CadastroStatus | None = None,
) -> dict:
    result = await PoliticaCancelamentoService(session).list_items(
        PageParams(page=page, size=size), canal=canal, status=status, search=q
    )
    return _page_dict(result, PoliticaRead)


@router.post(
    "/politicas",
    response_model=PoliticaRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_create_politica(
    payload: PoliticaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.criar"))
    ],
) -> PoliticaRead:
    item = await PoliticaCancelamentoService(session).create(
        current_user.tenant_id, payload
    )
    return PoliticaRead.model_validate(item)


@router.get("/politicas/{item_id}", response_model=PoliticaRead)
async def api_get_politica(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.visualizar"))
    ],
) -> PoliticaRead:
    return PoliticaRead.model_validate(
        await PoliticaCancelamentoService(session).get(item_id)
    )


@router.patch("/politicas/{item_id}", response_model=PoliticaRead)
async def api_update_politica(
    item_id: uuid.UUID,
    payload: PoliticaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.editar"))
    ],
) -> PoliticaRead:
    return PoliticaRead.model_validate(
        await PoliticaCancelamentoService(session).update(item_id, payload)
    )


@router.delete(
    "/politicas/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_politica(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.excluir"))
    ],
) -> Response:
    await PoliticaCancelamentoService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/politicas/{item_id}/faixas", response_model=dict)
async def api_list_politica_faixas(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.visualizar"))
    ],
) -> dict:
    items = await PoliticaCancelamentoService(session).list_faixas(item_id)
    return {"items": [PoliticaFaixaRead.model_validate(i) for i in items]}


@router.post(
    "/politicas/{item_id}/faixas",
    response_model=PoliticaFaixaRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_add_politica_faixa(
    item_id: uuid.UUID,
    payload: PoliticaFaixaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.editar"))
    ],
) -> PoliticaFaixaRead:
    item = await PoliticaCancelamentoService(session).add_faixa(
        current_user.tenant_id, item_id, payload
    )
    return PoliticaFaixaRead.model_validate(item)


@router.patch("/politicas/{item_id}/faixas/{faixa_id}", response_model=PoliticaFaixaRead)
async def api_update_politica_faixa(
    item_id: uuid.UUID,
    faixa_id: uuid.UUID,
    payload: PoliticaFaixaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.editar"))
    ],
) -> PoliticaFaixaRead:
    item = await PoliticaCancelamentoService(session).update_faixa(
        item_id, faixa_id, payload
    )
    return PoliticaFaixaRead.model_validate(item)


@router.delete(
    "/politicas/{item_id}/faixas/{faixa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_remove_politica_faixa(
    item_id: uuid.UUID,
    faixa_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.politica.editar"))
    ],
) -> Response:
    await PoliticaCancelamentoService(session).remove_faixa(item_id, faixa_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------------- Pricing
@router.post("/pricing/calcular", response_model=PricingQuoteResult)
async def api_calcular_pricing(
    payload: PricingQuoteRequest,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.simular.visualizar"))
    ],
) -> PricingQuoteResult:
    quote_input = PricingQuoteInput(
        tenant_id=current_user.tenant_id,
        **payload.model_dump(),
    )
    return await PricingService(session).calcular(quote_input)


@router.post("/pricing/cancelamento", response_model=CancelamentoSimulacao)
async def api_simular_cancelamento(
    payload: CancelamentoSimulacaoRequest,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("tarifario.simular.visualizar"))
    ],
) -> CancelamentoSimulacao:
    return await PricingService(session).simular_cancelamento(
        payload.politica_id,
        payload.valor_reserva,
        payload.horas_antes_retirada,
        diaria_unitaria=payload.diaria_unitaria,
        dias_locacao=payload.dias_locacao,
    )
