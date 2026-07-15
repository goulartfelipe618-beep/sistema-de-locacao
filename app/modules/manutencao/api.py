"""API REST do módulo Manutenção."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.identity.service import AuthenticatedUser
from app.modules.manutencao.schemas import (
    EstoqueAjusteRequest,
    EstoqueAlertaItem,
    EstoqueEntradaRequest,
    EstoqueMovimentoRead,
    EstoquePecaRead,
    EstoqueSaidaRequest,
    EstoqueTransferenciaRequest,
    OrdemServicoAprovar,
    OrdemServicoCancelar,
    OrdemServicoConcluir,
    OrdemServicoCreate,
    OrdemServicoFotoCreate,
    OrdemServicoFotoRead,
    OrdemServicoItemCreate,
    OrdemServicoItemRead,
    OrdemServicoRead,
    OrdemServicoStatusChange,
    OrdemServicoUpdate,
    PecaCreate,
    PecaRead,
    PecaUpdate,
    PlanoPreventivoCreate,
    PlanoPreventivoRead,
    PlanoPreventivoUpdate,
    PneuCreate,
    PneuDescartar,
    PneuAlertaItem,
    PneuHistoricoRead,
    PneuInstalar,
    PneuInspecionar,
    PneuRead,
    PneuRodizio,
    PneuUpdate,
    VeiculoPlanoLink,
    VeiculoPlanoRead,
)
from app.modules.manutencao.service import (
    EstoqueService,
    OrdemServicoService,
    OsFotoRepository,
    OsItemRepository,
    PecaService,
    PlanoPreventivoService,
    PneuHistoricoRepository,
    PneuService,
)
from app.shared.enums import OrdemServicoStatus, OrdemServicoTipo, PneuStatus

router = APIRouter(prefix="/manutencao", tags=["Manutenção"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


# ------------------------------------------------------------------ Ordem de Serviço
@router.get("/os", response_model=dict)
async def api_list_os(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: OrdemServicoStatus | None = None,
    tipo: OrdemServicoTipo | None = None,
) -> dict:
    result = await OrdemServicoService(session).list_items(
        PageParams(page=page, size=size), search=q, status=status, tipo=tipo
    )
    return _page_dict(result, OrdemServicoRead)


@router.post("/os", response_model=OrdemServicoRead, status_code=status.HTTP_201_CREATED)
async def api_create_os(
    payload: OrdemServicoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.criar"))
    ],
) -> OrdemServicoRead:
    item = await OrdemServicoService(session).create(current_user.tenant_id, payload)
    return OrdemServicoRead.model_validate(item)


@router.get("/os/{item_id}", response_model=OrdemServicoRead)
async def api_get_os(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.visualizar"))
    ],
) -> OrdemServicoRead:
    return OrdemServicoRead.model_validate(await OrdemServicoService(session).get(item_id))


@router.patch("/os/{item_id}", response_model=OrdemServicoRead)
async def api_update_os(
    item_id: uuid.UUID,
    payload: OrdemServicoUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> OrdemServicoRead:
    return OrdemServicoRead.model_validate(
        await OrdemServicoService(session).update(item_id, payload)
    )


@router.post("/os/{item_id}/status", response_model=OrdemServicoRead)
async def api_change_os_status(
    item_id: uuid.UUID,
    payload: OrdemServicoStatusChange,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> OrdemServicoRead:
    return OrdemServicoRead.model_validate(
        await OrdemServicoService(session).change_status(item_id, payload)
    )


@router.post("/os/{item_id}/concluir", response_model=OrdemServicoRead)
async def api_concluir_os(
    item_id: uuid.UUID,
    payload: OrdemServicoConcluir,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> OrdemServicoRead:
    return OrdemServicoRead.model_validate(
        await OrdemServicoService(session).concluir(item_id, payload)
    )


@router.post("/os/{item_id}/cancelar", response_model=OrdemServicoRead)
async def api_cancelar_os(
    item_id: uuid.UUID,
    payload: OrdemServicoCancelar,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> OrdemServicoRead:
    return OrdemServicoRead.model_validate(
        await OrdemServicoService(session).cancelar(item_id, payload)
    )


@router.post("/os/{item_id}/aprovar", response_model=OrdemServicoRead)
async def api_aprovar_os(
    item_id: uuid.UUID,
    payload: OrdemServicoAprovar,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.aprovar"))
    ],
) -> OrdemServicoRead:
    return OrdemServicoRead.model_validate(
        await OrdemServicoService(session).aprovar(item_id, payload)
    )


@router.get("/os/{item_id}/itens", response_model=dict)
async def api_list_os_itens(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.visualizar"))
    ],
) -> dict:
    await OrdemServicoService(session).get(item_id)
    repo = OsItemRepository(session)
    items = list((await session.execute(repo.list_by_os(item_id))).scalars().all())
    return {"items": [OrdemServicoItemRead.model_validate(i) for i in items]}


@router.post(
    "/os/{item_id}/itens",
    response_model=OrdemServicoItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_add_os_item(
    item_id: uuid.UUID,
    payload: OrdemServicoItemCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> OrdemServicoItemRead:
    item = await OrdemServicoService(session).add_item(
        current_user.tenant_id, item_id, payload
    )
    return OrdemServicoItemRead.model_validate(item)


@router.delete(
    "/os/{item_id}/itens/{os_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_remove_os_item(
    item_id: uuid.UUID,
    os_item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> Response:
    await OrdemServicoService(session).remove_item(item_id, os_item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/os/{item_id}/fotos", response_model=dict)
async def api_list_os_fotos(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.visualizar"))
    ],
) -> dict:
    await OrdemServicoService(session).get(item_id)
    repo = OsFotoRepository(session)
    fotos = list((await session.execute(repo.list_by_os(item_id))).scalars().all())
    return {"items": [OrdemServicoFotoRead.model_validate(f) for f in fotos]}


@router.post(
    "/os/{item_id}/fotos",
    response_model=OrdemServicoFotoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_add_os_foto(
    item_id: uuid.UUID,
    payload: OrdemServicoFotoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> OrdemServicoFotoRead:
    foto = await OrdemServicoService(session).add_foto(
        current_user.tenant_id, item_id, payload
    )
    return OrdemServicoFotoRead.model_validate(foto)


@router.delete(
    "/os/{item_id}/fotos/{foto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_remove_os_foto(
    item_id: uuid.UUID,
    foto_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.os.editar"))
    ],
) -> Response:
    await OrdemServicoService(session).remove_foto(item_id, foto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------- Preventiva
@router.get("/preventiva", response_model=dict)
async def api_list_preventiva(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("manutencao.preventiva.visualizar")),
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    result = await PlanoPreventivoService(session).list_items(
        PageParams(page=page, size=size), search=q
    )
    return _page_dict(result, PlanoPreventivoRead)


@router.post(
    "/preventiva",
    response_model=PlanoPreventivoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_create_preventiva(
    payload: PlanoPreventivoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.preventiva.criar"))
    ],
) -> PlanoPreventivoRead:
    item = await PlanoPreventivoService(session).create(current_user.tenant_id, payload)
    return PlanoPreventivoRead.model_validate(item)


@router.get("/preventiva/proximas", response_model=dict)
async def api_proximas_preventivas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("manutencao.preventiva.visualizar")),
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    items = await PlanoPreventivoService(session).proximas_preventivas(
        PageParams(page=page, size=size)
    )
    return {
        "items": items,
        "total": len(items),
        "page": page,
        "size": size,
        "pages": 1 if items else 0,
    }


@router.get("/preventiva/{item_id}", response_model=PlanoPreventivoRead)
async def api_get_preventiva(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("manutencao.preventiva.visualizar")),
    ],
) -> PlanoPreventivoRead:
    return PlanoPreventivoRead.model_validate(
        await PlanoPreventivoService(session).get(item_id)
    )


@router.patch("/preventiva/{item_id}", response_model=PlanoPreventivoRead)
async def api_update_preventiva(
    item_id: uuid.UUID,
    payload: PlanoPreventivoUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.preventiva.editar"))
    ],
) -> PlanoPreventivoRead:
    return PlanoPreventivoRead.model_validate(
        await PlanoPreventivoService(session).update(item_id, payload)
    )


@router.delete(
    "/preventiva/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_preventiva(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.preventiva.excluir"))
    ],
) -> Response:
    await PlanoPreventivoService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/preventiva/{item_id}/vincular",
    response_model=VeiculoPlanoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_vincular_preventiva(
    item_id: uuid.UUID,
    payload: VeiculoPlanoLink,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.preventiva.editar"))
    ],
) -> VeiculoPlanoRead:
    vinculo = await PlanoPreventivoService(session).link_veiculo(
        current_user.tenant_id, item_id, payload
    )
    return VeiculoPlanoRead.model_validate(vinculo)


@router.post(
    "/preventiva/gerar-os/{veiculo_plano_id}",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_gerar_os_preventiva(
    veiculo_plano_id: uuid.UUID,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.preventiva.criar"))
    ],
) -> OrdemServicoRead:
    item = await PlanoPreventivoService(session).gerar_os_preventiva(
        current_user.tenant_id, veiculo_plano_id
    )
    return OrdemServicoRead.model_validate(item)


# ------------------------------------------------------------------ Corretivas
@router.get("/corretivas", response_model=dict)
async def api_list_corretivas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("manutencao.corretiva.visualizar")),
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: OrdemServicoStatus | None = None,
) -> dict:
    result = await OrdemServicoService(session).list_corretivas(
        PageParams(page=page, size=size), search=q, status=status
    )
    return _page_dict(result, OrdemServicoRead)


# ------------------------------------------------------------------------- Peças
@router.get("/pecas", response_model=dict)
async def api_list_pecas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    result = await PecaService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, PecaRead)


@router.post("/pecas", response_model=PecaRead, status_code=status.HTTP_201_CREATED)
async def api_create_peca(
    payload: PecaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.criar"))
    ],
) -> PecaRead:
    item = await PecaService(session).create(current_user.tenant_id, payload)
    return PecaRead.model_validate(item)


@router.get("/pecas/{item_id}", response_model=PecaRead)
async def api_get_peca(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.visualizar"))
    ],
) -> PecaRead:
    return PecaRead.model_validate(await PecaService(session).get(item_id))


@router.patch("/pecas/{item_id}", response_model=PecaRead)
async def api_update_peca(
    item_id: uuid.UUID,
    payload: PecaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.editar"))
    ],
) -> PecaRead:
    return PecaRead.model_validate(await PecaService(session).update(item_id, payload))


@router.delete(
    "/pecas/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_peca(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.excluir"))
    ],
) -> Response:
    await PecaService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------- Estoque
@router.get("/estoque", response_model=dict)
async def api_list_estoque(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    filial_id: uuid.UUID | None = None,
    q: str | None = None,
) -> dict:
    result = await EstoqueService(session).list_estoque(
        PageParams(page=page, size=size), filial_id=filial_id, search=q
    )
    return _page_dict(result, EstoquePecaRead)


@router.get("/estoque/alertas", response_model=dict)
async def api_estoque_alertas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await EstoqueService(session).list_alertas(PageParams(page=page, size=size))
    return _page_dict(result, EstoqueAlertaItem)


@router.post(
    "/estoque/entrada",
    response_model=EstoqueMovimentoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_estoque_entrada(
    payload: EstoqueEntradaRequest,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.editar"))
    ],
) -> EstoqueMovimentoRead:
    from app.modules.manutencao.schemas import EstoqueEntrada

    data = payload.model_dump(exclude={"peca_id"})
    mov = await EstoqueService(session).entrada(
        current_user.tenant_id,
        payload.peca_id,
        EstoqueEntrada(**data),
    )
    return EstoqueMovimentoRead.model_validate(mov)


@router.post(
    "/estoque/saida",
    response_model=EstoqueMovimentoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_estoque_saida(
    payload: EstoqueSaidaRequest,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.editar"))
    ],
) -> EstoqueMovimentoRead:
    from app.modules.manutencao.schemas import EstoqueSaida

    data = payload.model_dump(exclude={"peca_id"})
    mov = await EstoqueService(session).saida(
        current_user.tenant_id, payload.peca_id, EstoqueSaida(**data)
    )
    return EstoqueMovimentoRead.model_validate(mov)


@router.post(
    "/estoque/ajuste",
    response_model=EstoqueMovimentoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_estoque_ajuste(
    payload: EstoqueAjusteRequest,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.editar"))
    ],
) -> EstoqueMovimentoRead:
    from app.modules.manutencao.schemas import EstoqueAjuste

    data = payload.model_dump(exclude={"peca_id"})
    mov = await EstoqueService(session).ajuste(
        current_user.tenant_id, payload.peca_id, EstoqueAjuste(**data)
    )
    return EstoqueMovimentoRead.model_validate(mov)


@router.post(
    "/estoque/transferencia",
    response_model=EstoqueMovimentoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_estoque_transferencia(
    payload: EstoqueTransferenciaRequest,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.peca.editar"))
    ],
) -> EstoqueMovimentoRead:
    from app.modules.manutencao.schemas import EstoqueTransferencia

    data = payload.model_dump(exclude={"peca_id"})
    mov = await EstoqueService(session).transferencia(
        current_user.tenant_id, payload.peca_id, EstoqueTransferencia(**data)
    )
    return EstoqueMovimentoRead.model_validate(mov)


# ------------------------------------------------------------------------- Pneus
@router.get("/pneus", response_model=dict)
async def api_list_pneus(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: PneuStatus | None = None,
) -> dict:
    result = await PneuService(session).list_items(
        PageParams(page=page, size=size), search=q, status=status
    )
    return _page_dict(result, PneuRead)


@router.get("/pneus/alertas", response_model=dict)
async def api_pneus_alertas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await PneuService(session).alertas_vida_util(PageParams(page=page, size=size))
    return _page_dict(result, PneuAlertaItem)


@router.post("/pneus", response_model=PneuRead, status_code=status.HTTP_201_CREATED)
async def api_create_pneu(
    payload: PneuCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.criar"))
    ],
) -> PneuRead:
    item = await PneuService(session).create(current_user.tenant_id, payload)
    return PneuRead.model_validate(item)


@router.get("/pneus/{item_id}", response_model=PneuRead)
async def api_get_pneu(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.visualizar"))
    ],
) -> PneuRead:
    return PneuRead.model_validate(await PneuService(session).get(item_id))


@router.patch("/pneus/{item_id}", response_model=PneuRead)
async def api_update_pneu(
    item_id: uuid.UUID,
    payload: PneuUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.editar"))
    ],
) -> PneuRead:
    return PneuRead.model_validate(await PneuService(session).update(item_id, payload))


@router.delete(
    "/pneus/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_pneu(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.excluir"))
    ],
) -> Response:
    await PneuService(session).delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/pneus/{item_id}/instalar", response_model=PneuRead)
async def api_instalar_pneu(
    item_id: uuid.UUID,
    payload: PneuInstalar,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.editar"))
    ],
) -> PneuRead:
    return PneuRead.model_validate(
        await PneuService(session).instalar(current_user.tenant_id, item_id, payload)
    )


@router.post("/pneus/{item_id}/rodizio", response_model=PneuRead)
async def api_rodizio_pneu(
    item_id: uuid.UUID,
    payload: PneuRodizio,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.editar"))
    ],
) -> PneuRead:
    return PneuRead.model_validate(
        await PneuService(session).rodizio(current_user.tenant_id, item_id, payload)
    )


@router.post("/pneus/{item_id}/inspecionar", response_model=PneuRead)
async def api_inspecionar_pneu(
    item_id: uuid.UUID,
    payload: PneuInspecionar,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.editar"))
    ],
) -> PneuRead:
    return PneuRead.model_validate(
        await PneuService(session).inspecionar(current_user.tenant_id, item_id, payload)
    )


@router.post("/pneus/{item_id}/descartar", response_model=PneuRead)
async def api_descartar_pneu(
    item_id: uuid.UUID,
    payload: PneuDescartar,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.editar"))
    ],
) -> PneuRead:
    return PneuRead.model_validate(
        await PneuService(session).descartar(current_user.tenant_id, item_id, payload)
    )


@router.get("/pneus/{item_id}/historico", response_model=dict)
async def api_pneu_historico(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("manutencao.pneu.visualizar"))
    ],
) -> dict:
    await PneuService(session).get(item_id)
    repo = PneuHistoricoRepository(session)
    rows = list((await session.execute(repo.list_by_pneu(item_id))).scalars().all())
    return {"items": [PneuHistoricoRead.model_validate(r) for r in rows]}
