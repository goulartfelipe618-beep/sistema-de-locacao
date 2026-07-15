"""API REST do módulo Locações."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.identity.service import AuthenticatedUser
from app.modules.locacoes.schemas import (
    AvariaCreate,
    AvariaRead,
    AvariaResponsabilidadeInput,
    AvariaUpdate,
    CheckoutConcluirInput,
    CheckinConcluirInput,
    ContratoCancelInput,
    ContratoCreate,
    ContratoRead,
    ContratoUpdate,
    MultaCreate,
    MultaRead,
    MultaUpdate,
    ReabrirInput,
    RenovacaoInput,
)
from app.modules.locacoes.service import (
    AvariaService,
    CheckinService,
    CheckoutService,
    ContratoService,
    EncerramentoService,
    MultaService,
    RenovacaoService,
)
from app.modules.reservas.service import ReservaService
from app.modules.tarifario.schemas import PricingQuoteInput
from app.modules.tarifario.service import PricingService
from app.shared.enums import (
    AvariaStatus,
    ContratoStatus,
    MultaStatus,
    TarifarioCanal,
)

router = APIRouter(prefix="/locacoes", tags=["Locações"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


# ------------------------------------------------------------------ Contratos
@router.get("/contratos", response_model=dict)
async def api_list_contratos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.contrato.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: ContratoStatus | None = None,
    cliente_id: uuid.UUID | None = None,
    veiculo_id: uuid.UUID | None = None,
    reserva_id: uuid.UUID | None = None,
) -> dict:
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=size),
        status=status,
        cliente_id=cliente_id,
        veiculo_id=veiculo_id,
        reserva_id=reserva_id,
        search=q,
    )
    return _page_dict(result, ContratoRead)


@router.post("/contratos", response_model=ContratoRead, status_code=status.HTTP_201_CREATED)
async def api_create_contrato(
    payload: ContratoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.contrato.criar"))
    ],
) -> ContratoRead:
    item = await ContratoService(session).create(current_user.tenant_id, payload)
    return ContratoRead.model_validate(item)


@router.get("/contratos/{contrato_id}", response_model=ContratoRead)
async def api_get_contrato(
    contrato_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.contrato.visualizar"))
    ],
) -> ContratoRead:
    return ContratoRead.model_validate(await ContratoService(session).get(contrato_id))


@router.patch("/contratos/{contrato_id}", response_model=ContratoRead)
async def api_update_contrato(
    contrato_id: uuid.UUID,
    payload: ContratoUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.contrato.editar"))
    ],
) -> ContratoRead:
    return ContratoRead.model_validate(
        await ContratoService(session).update(contrato_id, payload)
    )


@router.post("/contratos/{contrato_id}/cancelar", response_model=ContratoRead)
async def api_cancelar_contrato(
    contrato_id: uuid.UUID,
    payload: ContratoCancelInput,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.contrato.cancelar"))
    ],
) -> ContratoRead:
    return ContratoRead.model_validate(
        await ContratoService(session).cancelar(contrato_id, payload)
    )


@router.post(
    "/contratos/de-reserva/{reserva_id}",
    response_model=ContratoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_contrato_de_reserva(
    reserva_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.contrato.criar"))
    ],
) -> ContratoRead:
    contrato = await ReservaService(session).create_contrato(reserva_id)
    return ContratoRead.model_validate(contrato)


# ------------------------------------------------------------------ Check-out
@router.get("/checkout", response_model=dict)
async def api_list_checkout(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.checkout.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=size),
        statuses={ContratoStatus.AGUARDANDO_CHECKOUT, ContratoStatus.RASCUNHO},
    )
    return _page_dict(result, ContratoRead)


@router.post("/checkout/{contrato_id}/iniciar", response_model=ContratoRead)
async def api_checkout_iniciar(
    contrato_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.checkout.editar"))
    ],
) -> ContratoRead:
    return ContratoRead.model_validate(
        await CheckoutService(session).iniciar(contrato_id)
    )


@router.post("/checkout/{contrato_id}/concluir", response_model=ContratoRead)
async def api_checkout_concluir(
    contrato_id: uuid.UUID,
    payload: CheckoutConcluirInput,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.checkout.criar"))
    ],
) -> ContratoRead:
    if payload.realizado_por_user_id is None:
        payload = payload.model_copy(update={"realizado_por_user_id": current_user.id})
    return ContratoRead.model_validate(
        await CheckoutService(session).concluir(contrato_id, payload)
    )


# ------------------------------------------------------------------ Check-in
@router.get("/checkin", response_model=dict)
async def api_list_checkin(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.checkin.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=size),
        statuses={ContratoStatus.ATIVO, ContratoStatus.AGUARDANDO_CHECKIN},
    )
    return _page_dict(result, ContratoRead)


@router.post("/checkin/{contrato_id}/concluir", response_model=ContratoRead)
async def api_checkin_concluir(
    contrato_id: uuid.UUID,
    payload: CheckinConcluirInput,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.checkin.criar"))
    ],
) -> ContratoRead:
    if payload.realizado_por_user_id is None:
        payload = payload.model_copy(update={"realizado_por_user_id": current_user.id})
    return ContratoRead.model_validate(
        await CheckinService(session).concluir(contrato_id, payload)
    )


# ------------------------------------------------------------------ Renovações
@router.get("/renovacoes", response_model=dict)
async def api_list_renovacoes(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.renovacao.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=size),
        status=ContratoStatus.ATIVO,
    )
    return _page_dict(result, ContratoRead)


@router.get("/renovacoes/preview")
async def api_renovacao_preview(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.renovacao.visualizar"))
    ],
    contrato_id: uuid.UUID,
    nova_devolucao: datetime,
) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    quote = await PricingService(session).calcular(
        PricingQuoteInput(
            tenant_id=current_user.tenant_id,
            filial_id=contrato.filial_retirada_id,
            categoria_id=contrato.categoria_id,
            canal=TarifarioCanal.BALCAO,
            retirada_em=contrato.devolucao_prevista_em,
            devolucao_em=nova_devolucao,
            veiculo_id=contrato.veiculo_id,
            cliente_id=contrato.cliente_id,
        )
    )
    return {
        "contrato_id": contrato_id,
        "nova_devolucao": nova_devolucao,
        "dias_extra": quote.dias,
        "valor_aditivo": quote.total,
    }


@router.post("/renovacoes/{contrato_id}", response_model=ContratoRead)
async def api_renovar_contrato(
    contrato_id: uuid.UUID,
    payload: RenovacaoInput,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.renovacao.criar"))
    ],
) -> ContratoRead:
    return ContratoRead.model_validate(
        await RenovacaoService(session).renovar(contrato_id, payload)
    )


# ------------------------------------------------------------------ Encerramentos
@router.get("/encerramentos", response_model=dict)
async def api_list_encerramentos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("locacoes.encerramento.visualizar")),
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: ContratoStatus | None = None,
    pendencia_financeira: bool | None = None,
) -> dict:
    if status:
        result = await ContratoService(session).list_items(
            PageParams(page=page, size=size),
            status=status,
            search=q,
        )
    else:
        result = await EncerramentoService(session).list_encerrados(
            PageParams(page=page, size=size),
            pendencia_financeira=pendencia_financeira,
            search=q,
        )
    return _page_dict(result, ContratoRead)


@router.post("/encerramentos/{contrato_id}/reabrir", response_model=ContratoRead)
async def api_reabrir_contrato(
    contrato_id: uuid.UUID,
    payload: ReabrirInput,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("locacoes.encerramento.reabrir")),
    ],
) -> ContratoRead:
    return ContratoRead.model_validate(
        await EncerramentoService(session).reabrir(contrato_id, payload)
    )


# ------------------------------------------------------------------ Multas
@router.get("/multas", response_model=dict)
async def api_list_multas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status: MultaStatus | None = None,
    veiculo_id: uuid.UUID | None = None,
    contrato_id: uuid.UUID | None = None,
    cliente_id: uuid.UUID | None = None,
) -> dict:
    result = await MultaService(session).list_items(
        PageParams(page=page, size=size),
        status=status,
        veiculo_id=veiculo_id,
        contrato_id=contrato_id,
        cliente_id=cliente_id,
    )
    return _page_dict(result, MultaRead)


@router.post("/multas", response_model=MultaRead, status_code=status.HTTP_201_CREATED)
async def api_create_multa(
    payload: MultaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.criar"))
    ],
) -> MultaRead:
    item = await MultaService(session).create(current_user.tenant_id, payload)
    return MultaRead.model_validate(item)


@router.get("/multas/{multa_id}", response_model=MultaRead)
async def api_get_multa(
    multa_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.visualizar"))
    ],
) -> MultaRead:
    return MultaRead.model_validate(await MultaService(session).get(multa_id))


@router.patch("/multas/{multa_id}", response_model=MultaRead)
async def api_update_multa(
    multa_id: uuid.UUID,
    payload: MultaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.editar"))
    ],
) -> MultaRead:
    return MultaRead.model_validate(
        await MultaService(session).update(multa_id, payload)
    )


@router.delete(
    "/multas/{multa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_multa(
    multa_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.excluir"))
    ],
) -> Response:
    await MultaService(session).delete(multa_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/multas/{multa_id}/vincular", response_model=MultaRead)
async def api_vincular_multa(
    multa_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.editar"))
    ],
) -> MultaRead:
    return MultaRead.model_validate(
        await MultaService(session).vincular_auto(multa_id)
    )


@router.post("/multas/{multa_id}/notificado", response_model=MultaRead)
async def api_multa_notificado(
    multa_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.editar"))
    ],
) -> MultaRead:
    return MultaRead.model_validate(
        await MultaService(session).marcar_notificado(multa_id)
    )


@router.post("/multas/{multa_id}/paga", response_model=MultaRead)
async def api_multa_paga(
    multa_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.multa.editar"))
    ],
) -> MultaRead:
    return MultaRead.model_validate(await MultaService(session).marcar_paga(multa_id))


# ------------------------------------------------------------------ Avarias
@router.get("/avarias", response_model=dict)
async def api_list_avarias(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.avaria.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status: AvariaStatus | None = None,
    veiculo_id: uuid.UUID | None = None,
    contrato_id: uuid.UUID | None = None,
) -> dict:
    result = await AvariaService(session).list_items(
        PageParams(page=page, size=size),
        status=status,
        veiculo_id=veiculo_id,
        contrato_id=contrato_id,
    )
    return _page_dict(result, AvariaRead)


@router.post("/avarias", response_model=AvariaRead, status_code=status.HTTP_201_CREATED)
async def api_create_avaria(
    payload: AvariaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.avaria.criar"))
    ],
) -> AvariaRead:
    item = await AvariaService(session).create(current_user.tenant_id, payload)
    return AvariaRead.model_validate(item)


@router.get("/avarias/{avaria_id}", response_model=AvariaRead)
async def api_get_avaria(
    avaria_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.avaria.visualizar"))
    ],
) -> AvariaRead:
    return AvariaRead.model_validate(await AvariaService(session).get(avaria_id))


@router.patch("/avarias/{avaria_id}", response_model=AvariaRead)
async def api_update_avaria(
    avaria_id: uuid.UUID,
    payload: AvariaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.avaria.editar"))
    ],
) -> AvariaRead:
    return AvariaRead.model_validate(
        await AvariaService(session).update(avaria_id, payload)
    )


@router.post("/avarias/{avaria_id}/responsabilidade", response_model=AvariaRead)
async def api_avaria_responsabilidade(
    avaria_id: uuid.UUID,
    payload: AvariaResponsabilidadeInput,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.avaria.editar"))
    ],
) -> AvariaRead:
    return AvariaRead.model_validate(
        await AvariaService(session).definir_responsabilidade(avaria_id, payload)
    )


@router.post("/avarias/{avaria_id}/gerar-os", response_model=AvariaRead)
async def api_avaria_gerar_os(
    avaria_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.avaria.editar"))
    ],
) -> AvariaRead:
    return AvariaRead.model_validate(await AvariaService(session).gerar_os(avaria_id))


@router.post("/avarias/{avaria_id}/encerrar", response_model=AvariaRead)
async def api_avaria_encerrar(
    avaria_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("locacoes.avaria.editar"))
    ],
) -> AvariaRead:
    return AvariaRead.model_validate(await AvariaService(session).encerrar(avaria_id))
