"""API REST do módulo Comercial / CRM (§7)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.comercial.schemas import (
    CampanhaCreate,
    CampanhaRead,
    CampanhaUpdate,
    CupomCreate,
    CupomRead,
    CupomUpdate,
    CupomValidacaoResult,
    CupomValidarInput,
    FidelidadeContaRead,
    FidelidadeResgatarInput,
    InteracaoCreate,
    InteracaoRead,
    MarcarGanhoInput,
    MarcarPerdidoInput,
    MoverEstagioInput,
    OportunidadeCreate,
    OportunidadeRead,
    OportunidadeUpdate,
    PropostaCreate,
    PropostaRead,
    PropostaUpdate,
)
from app.modules.comercial.service import (
    CampanhaService,
    CupomService,
    FidelidadeService,
    FunilService,
    PropostaService,
)
from app.modules.identity.service import AuthenticatedUser
from app.shared.enums import (
    CrmCampanhaStatus,
    CrmCupomStatus,
    CrmEstagio,
    CrmPropostaStatus,
)

router = APIRouter(prefix="/comercial", tags=["Comercial / CRM"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


# ------------------------------------------------------------------ Funil
@router.get("/funil", response_model=dict)
async def api_list_funil(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    estagio: CrmEstagio | None = Query(None),
) -> dict:
    result = await FunilService(session).list_items(PageParams(page=page, size=size), estagio=estagio)
    return _page_dict(result, OportunidadeRead)


@router.post("/funil", response_model=OportunidadeRead, status_code=status.HTTP_201_CREATED)
async def api_create_oportunidade(
    payload: OportunidadeCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.criar"))],
) -> OportunidadeRead:
    return OportunidadeRead.model_validate(
        await FunilService(session).create(current_user.tenant_id, payload)
    )


@router.get("/funil/{oportunidade_id}", response_model=OportunidadeRead)
async def api_get_oportunidade(
    oportunidade_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.visualizar"))],
) -> OportunidadeRead:
    return OportunidadeRead.model_validate(await FunilService(session).get(oportunidade_id))


@router.patch("/funil/{oportunidade_id}", response_model=OportunidadeRead)
async def api_update_oportunidade(
    oportunidade_id: uuid.UUID,
    payload: OportunidadeUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.editar"))],
) -> OportunidadeRead:
    return OportunidadeRead.model_validate(
        await FunilService(session).update(oportunidade_id, payload)
    )


@router.post("/funil/{oportunidade_id}/mover", response_model=OportunidadeRead)
async def api_mover_estagio(
    oportunidade_id: uuid.UUID,
    payload: MoverEstagioInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.editar"))],
) -> OportunidadeRead:
    return OportunidadeRead.model_validate(
        await FunilService(session).move_estagio(oportunidade_id, payload.estagio)
    )


@router.post("/funil/{oportunidade_id}/perdido", response_model=OportunidadeRead)
async def api_marcar_perdido(
    oportunidade_id: uuid.UUID,
    payload: MarcarPerdidoInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.editar"))],
) -> OportunidadeRead:
    return OportunidadeRead.model_validate(
        await FunilService(session).marcar_perdido(oportunidade_id, payload.motivo_perda)
    )


@router.post("/funil/{oportunidade_id}/ganho", response_model=OportunidadeRead)
async def api_marcar_ganho(
    oportunidade_id: uuid.UUID,
    payload: MarcarGanhoInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.editar"))],
) -> OportunidadeRead:
    return OportunidadeRead.model_validate(
        await FunilService(session).marcar_ganho(oportunidade_id, reserva_id=payload.reserva_id)
    )


@router.post(
    "/funil/{oportunidade_id}/interacoes",
    response_model=InteracaoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_add_interacao(
    oportunidade_id: uuid.UUID,
    payload: InteracaoCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.funil.criar"))],
) -> InteracaoRead:
    return InteracaoRead.model_validate(
        await FunilService(session).add_interacao(oportunidade_id, payload, user_id=current_user.id)
    )


# ------------------------------------------------------------------ Propostas
@router.get("/propostas", response_model=dict)
async def api_list_propostas(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: CrmPropostaStatus | None = Query(None, alias="status"),
) -> dict:
    result = await PropostaService(session).list_items(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, PropostaRead)


@router.post("/propostas", response_model=PropostaRead, status_code=status.HTTP_201_CREATED)
async def api_create_proposta(
    payload: PropostaCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.criar"))],
) -> PropostaRead:
    return PropostaRead.model_validate(
        await PropostaService(session).create(current_user.tenant_id, payload)
    )


@router.get("/propostas/{proposta_id}", response_model=PropostaRead)
async def api_get_proposta(
    proposta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.visualizar"))],
) -> PropostaRead:
    return PropostaRead.model_validate(await PropostaService(session).get(proposta_id))


@router.patch("/propostas/{proposta_id}", response_model=PropostaRead)
async def api_update_proposta(
    proposta_id: uuid.UUID,
    payload: PropostaUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.editar"))],
) -> PropostaRead:
    return PropostaRead.model_validate(await PropostaService(session).update(proposta_id, payload))


@router.post("/propostas/{proposta_id}/enviar", response_model=PropostaRead)
async def api_enviar_proposta(
    proposta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.editar"))],
) -> PropostaRead:
    return PropostaRead.model_validate(await PropostaService(session).enviar(proposta_id))


@router.post("/propostas/{proposta_id}/aceitar", response_model=PropostaRead)
async def api_aceitar_proposta(
    proposta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.editar"))],
) -> PropostaRead:
    return PropostaRead.model_validate(await PropostaService(session).aceitar(proposta_id))


@router.post("/propostas/{proposta_id}/recusar", response_model=PropostaRead)
async def api_recusar_proposta(
    proposta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.editar"))],
) -> PropostaRead:
    return PropostaRead.model_validate(await PropostaService(session).recusar(proposta_id))


@router.post("/propostas/{proposta_id}/revisao", response_model=PropostaRead, status_code=status.HTTP_201_CREATED)
async def api_revisar_proposta(
    proposta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.editar"))],
) -> PropostaRead:
    return PropostaRead.model_validate(await PropostaService(session).criar_revisao(proposta_id))


@router.delete(
    "/propostas/{proposta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_proposta(
    proposta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.proposta.excluir"))],
) -> Response:
    await PropostaService(session).delete(proposta_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ Campanhas
@router.get("/campanhas", response_model=dict)
async def api_list_campanhas(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: CrmCampanhaStatus | None = Query(None, alias="status"),
) -> dict:
    result = await CampanhaService(session).list_items(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, CampanhaRead)


@router.post("/campanhas", response_model=CampanhaRead, status_code=status.HTTP_201_CREATED)
async def api_create_campanha(
    payload: CampanhaCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.criar"))],
) -> CampanhaRead:
    return CampanhaRead.model_validate(
        await CampanhaService(session).create(current_user.tenant_id, payload)
    )


@router.get("/campanhas/{campanha_id}", response_model=CampanhaRead)
async def api_get_campanha(
    campanha_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.visualizar"))],
) -> CampanhaRead:
    return CampanhaRead.model_validate(await CampanhaService(session).get(campanha_id))


@router.patch("/campanhas/{campanha_id}", response_model=CampanhaRead)
async def api_update_campanha(
    campanha_id: uuid.UUID,
    payload: CampanhaUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.editar"))],
) -> CampanhaRead:
    return CampanhaRead.model_validate(await CampanhaService(session).update(campanha_id, payload))


@router.post("/campanhas/{campanha_id}/ativar", response_model=CampanhaRead)
async def api_ativar_campanha(
    campanha_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.editar"))],
) -> CampanhaRead:
    return CampanhaRead.model_validate(await CampanhaService(session).ativar(campanha_id))


@router.post("/campanhas/{campanha_id}/pausar", response_model=CampanhaRead)
async def api_pausar_campanha(
    campanha_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.editar"))],
) -> CampanhaRead:
    return CampanhaRead.model_validate(await CampanhaService(session).pausar(campanha_id))


@router.post("/campanhas/{campanha_id}/encerrar", response_model=CampanhaRead)
async def api_encerrar_campanha(
    campanha_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.editar"))],
) -> CampanhaRead:
    return CampanhaRead.model_validate(await CampanhaService(session).encerrar(campanha_id))


@router.post("/campanhas/{campanha_id}/disparar", response_model=CampanhaRead)
async def api_disparar_campanha(
    campanha_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.editar"))],
) -> CampanhaRead:
    return CampanhaRead.model_validate(await CampanhaService(session).disparar(campanha_id))


@router.delete(
    "/campanhas/{campanha_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_campanha(
    campanha_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.campanha.excluir"))],
) -> Response:
    svc = CampanhaService(session)
    campanha = await svc.get(campanha_id)
    await svc.repo.delete(campanha)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ Cupons
@router.get("/cupons", response_model=dict)
async def api_list_cupons(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.cupom.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: CrmCupomStatus | None = Query(None, alias="status"),
) -> dict:
    result = await CupomService(session).list_items(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, CupomRead)


@router.post("/cupons", response_model=CupomRead, status_code=status.HTTP_201_CREATED)
async def api_create_cupom(
    payload: CupomCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.cupom.criar"))],
) -> CupomRead:
    return CupomRead.model_validate(await CupomService(session).create(current_user.tenant_id, payload))


@router.get("/cupons/{cupom_id}", response_model=CupomRead)
async def api_get_cupom(
    cupom_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.cupom.visualizar"))],
) -> CupomRead:
    return CupomRead.model_validate(await CupomService(session).get(cupom_id))


@router.patch("/cupons/{cupom_id}", response_model=CupomRead)
async def api_update_cupom(
    cupom_id: uuid.UUID,
    payload: CupomUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.cupom.editar"))],
) -> CupomRead:
    return CupomRead.model_validate(await CupomService(session).update(cupom_id, payload))


@router.delete(
    "/cupons/{cupom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_cupom(
    cupom_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.cupom.excluir"))],
) -> Response:
    await CupomService(session).delete(cupom_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cupons/validar", response_model=CupomValidacaoResult)
async def api_validar_cupom(
    payload: CupomValidarInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.cupom.visualizar"))],
) -> CupomValidacaoResult:
    return await CupomService(session).validar(payload)


# ------------------------------------------------------------------ Fidelidade
@router.get("/fidelidade/contas", response_model=dict)
async def api_list_contas(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.fidelidade.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await FidelidadeService(session).list_contas(PageParams(page=page, size=size))
    return _page_dict(result, FidelidadeContaRead)


@router.post("/fidelidade/resgatar", response_model=dict)
async def api_resgatar_pontos(
    payload: FidelidadeResgatarInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("comercial.fidelidade.editar"))],
) -> dict:
    _mov, valor = await FidelidadeService(session).resgatar(
        current_user.tenant_id,
        cliente_id=payload.cliente_id,
        pontos=payload.pontos,
        reserva_id=payload.reserva_id,
    )
    return {"pontos": payload.pontos, "valor_desconto": str(valor)}
