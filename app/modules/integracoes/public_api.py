"""API pública autenticada por API Key (§12.5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.integracoes.deps import PublicSessionDep, require_api_key_scope
from app.modules.integracoes.models import IntApiKey
from app.modules.locacoes.service import ContratoService
from app.modules.reservas.schemas import ReservaCreate
from app.modules.reservas.service import DisponibilidadeService, ReservaService

public_router = APIRouter(prefix="/public", tags=["API Pública"])


@public_router.get("/disponibilidade")
async def public_disponibilidade(
    session: PublicSessionDep,
    _key: Annotated[IntApiKey, Depends(require_api_key_scope("disponibilidade:read"))],
    filial_id: uuid.UUID = Query(...),
    retirada_em: datetime = Query(...),
    devolucao_em: datetime = Query(...),
) -> list[dict]:
    result = await DisponibilidadeService(session).consultar(
        filial_id, retirada_em, devolucao_em
    )
    return [
        {
            "categoria_id": str(r.categoria_id),
            "nome": r.nome,
            "livres": r.livres,
            "ocupados": r.ocupados,
            "total_frota": r.total_frota,
        }
        for r in result
    ]


@public_router.post("/reservas", status_code=201)
async def public_criar_reserva(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("reservas:write"))],
    payload: ReservaCreate,
) -> dict:
    reserva = await ReservaService(session).create(key.tenant_id, payload)
    return {"id": str(reserva.id), "numero": reserva.numero, "status": reserva.status.value}


@public_router.get("/contratos/{contrato_id}")
async def public_status_contrato(
    contrato_id: uuid.UUID,
    session: PublicSessionDep,
    _key: Annotated[IntApiKey, Depends(require_api_key_scope("contratos:read"))],
) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    return {
        "id": str(contrato.id),
        "numero": contrato.numero,
        "status": contrato.status.value,
        "cliente_id": str(contrato.cliente_id),
        "veiculo_id": str(contrato.veiculo_id),
    }
