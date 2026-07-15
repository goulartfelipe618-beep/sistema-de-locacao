"""API REST do módulo Reservas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.identity.service import AuthenticatedUser
from app.modules.reservas.schemas import (
    CalendarioEvento,
    CalendarioRealocarInput,
    CotacaoConverterInput,
    CotacaoCreate,
    CotacaoRead,
    CotacaoUpdate,
    DisponibilidadeCategoria,
    ReservaCancelInput,
    ReservaCreate,
    ReservaRead,
    ReservaUpdate,
)
from app.modules.reservas.service import (
    CalendarioService,
    CotacaoService,
    DisponibilidadeService,
    ReservaService,
)
from app.shared.enums import CotacaoStatus, ReservaStatus

router = APIRouter(prefix="/reservas", tags=["Reservas"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


# -------------------------------------------------------------- Disponibilidade
@router.get("/disponibilidade", response_model=list[DisponibilidadeCategoria])
async def api_disponibilidade(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("reservas.disponibilidade.visualizar")),
    ],
    filial_id: uuid.UUID,
    inicio: datetime,
    fim: datetime,
    categoria_id: uuid.UUID | None = None,
    buffer_horas: int = Query(2, ge=0, le=48),
    overbooking_pct: int = Query(0, ge=0, le=100),
) -> list[DisponibilidadeCategoria]:
    return await DisponibilidadeService(session).consultar(
        filial_id,
        inicio,
        fim,
        categoria_id=categoria_id,
        buffer_horas=buffer_horas,
        overbooking_pct=overbooking_pct,
    )


# ------------------------------------------------------------------ Calendário
@router.get("/calendario/events", response_model=list[CalendarioEvento])
async def api_calendario_events(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.calendario.visualizar"))
    ],
    inicio: datetime,
    fim: datetime,
    filial_id: uuid.UUID | None = None,
    categoria_id: uuid.UUID | None = None,
    veiculo_id: uuid.UUID | None = None,
) -> list[CalendarioEvento]:
    return await CalendarioService(session).list_events(
        inicio,
        fim,
        filial_id=filial_id,
        categoria_id=categoria_id,
        veiculo_id=veiculo_id,
    )


@router.post("/calendario/realocar", response_model=ReservaRead)
async def api_calendario_realocar(
    payload: CalendarioRealocarInput,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.editar"))
    ],
) -> ReservaRead:
    reserva = await CalendarioService(session).realocar(
        payload.reserva_id, payload.novo_veiculo_id
    )
    return ReservaRead.model_validate(reserva)


# --------------------------------------------------------------------- Cotações
@router.get("/cotacoes", response_model=dict)
async def api_list_cotacoes(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.cotacao.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: CotacaoStatus | None = None,
    cliente_id: uuid.UUID | None = None,
) -> dict:
    result = await CotacaoService(session).list_items(
        PageParams(page=page, size=size),
        status=status,
        cliente_id=cliente_id,
        search=q,
    )
    return _page_dict(result, CotacaoRead)


@router.post("/cotacoes", response_model=CotacaoRead, status_code=status.HTTP_201_CREATED)
async def api_create_cotacao(
    payload: CotacaoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.cotacao.criar"))
    ],
) -> CotacaoRead:
    item = await CotacaoService(session).create(current_user.tenant_id, payload)
    return CotacaoRead.model_validate(item)


@router.get("/cotacoes/{cotacao_id}", response_model=CotacaoRead)
async def api_get_cotacao(
    cotacao_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.cotacao.visualizar"))
    ],
) -> CotacaoRead:
    return CotacaoRead.model_validate(await CotacaoService(session).get(cotacao_id))


@router.patch("/cotacoes/{cotacao_id}", response_model=CotacaoRead)
async def api_update_cotacao(
    cotacao_id: uuid.UUID,
    payload: CotacaoUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.cotacao.editar"))
    ],
) -> CotacaoRead:
    return CotacaoRead.model_validate(
        await CotacaoService(session).update(cotacao_id, payload)
    )


@router.delete(
    "/cotacoes/{cotacao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_cotacao(
    cotacao_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.cotacao.excluir"))
    ],
) -> Response:
    await CotacaoService(session).delete(cotacao_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cotacoes/{cotacao_id}/converter", response_model=ReservaRead)
async def api_converter_cotacao(
    cotacao_id: uuid.UUID,
    payload: CotacaoConverterInput,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.cotacao.editar"))
    ],
) -> ReservaRead:
    reserva = await CotacaoService(session).converter_em_reserva(cotacao_id, payload)
    return ReservaRead.model_validate(reserva)


# ------------------------------------------------------------------ Reservas
@router.get("", response_model=dict)
async def api_list_reservas(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: ReservaStatus | None = None,
    cliente_id: uuid.UUID | None = None,
    veiculo_id: uuid.UUID | None = None,
    filial_id: uuid.UUID | None = None,
    retirada_de: datetime | None = None,
    retirada_ate: datetime | None = None,
) -> dict:
    result = await ReservaService(session).list_items(
        PageParams(page=page, size=size),
        status=status,
        cliente_id=cliente_id,
        veiculo_id=veiculo_id,
        filial_id=filial_id,
        retirada_de=retirada_de,
        retirada_ate=retirada_ate,
        search=q,
    )
    return _page_dict(result, ReservaRead)


@router.post("", response_model=ReservaRead, status_code=status.HTTP_201_CREATED)
async def api_create_reserva(
    payload: ReservaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.criar"))
    ],
) -> ReservaRead:
    item = await ReservaService(session).create(current_user.tenant_id, payload)
    return ReservaRead.model_validate(item)


@router.get("/{reserva_id}", response_model=ReservaRead)
async def api_get_reserva(
    reserva_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.visualizar"))
    ],
) -> ReservaRead:
    return ReservaRead.model_validate(await ReservaService(session).get(reserva_id))


@router.patch("/{reserva_id}", response_model=ReservaRead)
async def api_update_reserva(
    reserva_id: uuid.UUID,
    payload: ReservaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.editar"))
    ],
) -> ReservaRead:
    return ReservaRead.model_validate(
        await ReservaService(session).update(reserva_id, payload)
    )


@router.post("/{reserva_id}/confirmar", response_model=ReservaRead)
async def api_confirmar_reserva(
    reserva_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.editar"))
    ],
) -> ReservaRead:
    return ReservaRead.model_validate(
        await ReservaService(session).confirmar(reserva_id)
    )


@router.post("/{reserva_id}/aprovar", response_model=ReservaRead)
async def api_aprovar_reserva(
    reserva_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.aprovar"))
    ],
) -> ReservaRead:
    return ReservaRead.model_validate(
        await ReservaService(session).aprovar_bloqueado(reserva_id)
    )


@router.post("/{reserva_id}/cancelar", response_model=ReservaRead)
async def api_cancelar_reserva(
    reserva_id: uuid.UUID,
    payload: ReservaCancelInput,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.cancelar"))
    ],
) -> ReservaRead:
    return ReservaRead.model_validate(
        await ReservaService(session).cancelar(reserva_id, payload)
    )


@router.post("/{reserva_id}/no-show", response_model=ReservaRead)
async def api_no_show_reserva(
    reserva_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.editar"))
    ],
) -> ReservaRead:
    return ReservaRead.model_validate(
        await ReservaService(session).marcar_no_show(reserva_id)
    )


@router.post("/{reserva_id}/checkout", response_model=ReservaRead)
async def api_checkout_reserva(
    reserva_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("reservas.reserva.editar"))
    ],
) -> ReservaRead:
    return ReservaRead.model_validate(
        await ReservaService(session).checkout_realizado(reserva_id)
    )
