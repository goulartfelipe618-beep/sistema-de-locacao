"""API REST — módulo Intermediação."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.modules.identity.service import AuthenticatedUser
from app.modules.intermediacao.schemas import (
    AprovacaoPendenteRead,
    ContratoFornecedorCreate,
    ContratoFornecedorRead,
    ContratoFornecedorUpdate,
    ContratoPrecoCreate,
    IndisponibilidadeTerceiroCreate,
    IntermediacaoConfigRead,
    IntermediacaoConfigUpdate,
    RejeitarFornecedorInput,
    RepasseLancamentoRead,
)
from app.modules.intermediacao.service import IntermediacaoService

router = APIRouter(prefix="/intermediacao", tags=["Intermediação"])


def _config_read(cfg: Any) -> IntermediacaoConfigRead:
    return IntermediacaoConfigRead(
        modo_operacao=cfg.modo_operacao,
        exige_contrato_fornecedor=cfg.exige_contrato_fornecedor,
        aprovar_reserva_automaticamente=cfg.aprovar_reserva_automaticamente,
        publicar_terceiros_site=cfg.publicar_terceiros_site,
        margem_minima_percentual=cfg.margem_minima_percentual,
        buffer_disponibilidade_horas=cfg.buffer_disponibilidade_horas,
        priorizar_frota_propria=cfg.priorizar_frota_propria,
        observacoes=cfg.observacoes,
    )


@router.get("/config", response_model=IntermediacaoConfigRead)
async def api_get_config(
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.config.visualizar"))
    ],
) -> IntermediacaoConfigRead:
    cfg = await IntermediacaoService(session).get_config(user.tenant_id)
    return _config_read(cfg)


@router.put("/config", response_model=IntermediacaoConfigRead)
async def api_update_config(
    payload: IntermediacaoConfigUpdate,
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.config.editar"))
    ],
) -> IntermediacaoConfigRead:
    cfg = await IntermediacaoService(session).update_config(user.tenant_id, payload)
    return _config_read(cfg)


@router.get("/contratos-fornecedor", response_model=list[ContratoFornecedorRead])
async def api_list_contratos(
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.contrato.visualizar"))
    ],
    fornecedor_id: uuid.UUID | None = None,
) -> list[ContratoFornecedorRead]:
    rows = await IntermediacaoService(session).list_contratos_fornecedor(
        user.tenant_id, fornecedor_id=fornecedor_id
    )
    return [ContratoFornecedorRead.model_validate(r) for r in rows]


@router.post("/contratos-fornecedor", response_model=ContratoFornecedorRead, status_code=status.HTTP_201_CREATED)
async def api_create_contrato(
    payload: ContratoFornecedorCreate,
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.contrato.criar"))
    ],
) -> ContratoFornecedorRead:
    row = await IntermediacaoService(session).create_contrato_fornecedor(user.tenant_id, payload)
    return ContratoFornecedorRead.model_validate(row)


@router.patch("/contratos-fornecedor/{contrato_id}", response_model=ContratoFornecedorRead)
async def api_update_contrato(
    contrato_id: uuid.UUID,
    payload: ContratoFornecedorUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.contrato.editar"))
    ],
) -> ContratoFornecedorRead:
    row = await IntermediacaoService(session).update_contrato_fornecedor(contrato_id, payload)
    return ContratoFornecedorRead.model_validate(row)


@router.post("/contratos-fornecedor/{contrato_id}/precos", status_code=status.HTTP_201_CREATED)
async def api_add_preco(
    contrato_id: uuid.UUID,
    payload: ContratoPrecoCreate,
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.contrato.editar"))
    ],
) -> dict:
    preco = await IntermediacaoService(session).add_preco_contrato(
        user.tenant_id, contrato_id, payload
    )
    return {"id": str(preco.id)}


@router.get("/indisponibilidades")
async def api_list_indisponibilidades(
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("intermediacao.indisponibilidade.visualizar")),
    ],
) -> list[dict]:
    from sqlalchemy import select

    from app.modules.intermediacao.models import FrotaIndisponibilidadeTerceiro

    rows = list(
        (
            await session.execute(
                select(FrotaIndisponibilidadeTerceiro).where(
                    FrotaIndisponibilidadeTerceiro.tenant_id == user.tenant_id,
                    FrotaIndisponibilidadeTerceiro.deleted_at.is_(None),
                )
            )
        ).scalars().all()
    )
    return [
        {
            "id": str(r.id),
            "veiculo_id": str(r.veiculo_id),
            "fornecedor_id": str(r.fornecedor_id),
            "inicio_em": r.inicio_em.isoformat(),
            "fim_em": r.fim_em.isoformat() if r.fim_em else None,
            "motivo": r.motivo.value,
        }
        for r in rows
    ]


@router.post("/indisponibilidades", status_code=status.HTTP_201_CREATED)
async def api_create_indisponibilidade(
    payload: IndisponibilidadeTerceiroCreate,
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.indisponibilidade.criar"))
    ],
) -> dict:
    row = await IntermediacaoService(session).registrar_indisponibilidade(
        user.tenant_id, payload, user_id=user.id
    )
    return {"id": str(row.id)}


@router.post("/indisponibilidades/{indisp_id}/encerrar")
async def api_encerrar_indisponibilidade(
    indisp_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.indisponibilidade.editar"))
    ],
) -> dict:
    row = await IntermediacaoService(session).encerrar_indisponibilidade(indisp_id)
    return {"id": str(row.id), "fim_em": row.fim_em.isoformat() if row.fim_em else None}


@router.get("/repasses", response_model=list[RepasseLancamentoRead])
async def api_list_repasses(
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.repasse.visualizar"))
    ],
    fornecedor_id: uuid.UUID | None = None,
) -> list[RepasseLancamentoRead]:
    rows = await IntermediacaoService(session).list_repasse_lancamentos(
        user.tenant_id, fornecedor_id=fornecedor_id
    )
    return [RepasseLancamentoRead.model_validate(r) for r in rows]


@router.get("/aprovacoes-pendentes", response_model=list[AprovacaoPendenteRead])
async def api_aprovacoes_pendentes(
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.reserva.aprovar"))
    ],
) -> list[AprovacaoPendenteRead]:
    rows = await IntermediacaoService(session).list_aprovacoes_pendentes(user.tenant_id)
    return [
        AprovacaoPendenteRead(
            id=r.id,
            numero=r.numero,
            cliente_id=r.cliente_id,
            fornecedor_id=r.fornecedor_id,
            retirada_em=r.retirada_em,
            valor_total=r.valor_total,
            valor_repasse_total=r.valor_repasse_total,
            intermediacao_status=r.intermediacao_status,
        )
        for r in rows
    ]


@router.post("/reservas/{reserva_id}/aprovar-fornecedor")
async def api_aprovar_fornecedor(
    reserva_id: uuid.UUID,
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.reserva.aprovar"))
    ],
) -> dict:
    reserva = await IntermediacaoService(session).aprovar_reserva_fornecedor(
        reserva_id, user_id=user.id
    )
    return {"id": str(reserva.id), "intermediacao_status": reserva.intermediacao_status.value}


@router.post("/reservas/{reserva_id}/rejeitar-fornecedor")
async def api_rejeitar_fornecedor(
    reserva_id: uuid.UUID,
    payload: RejeitarFornecedorInput,
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.reserva.aprovar"))
    ],
) -> dict:
    reserva = await IntermediacaoService(session).rejeitar_reserva_fornecedor(
        reserva_id, payload.motivo, user_id=user.id
    )
    return {"id": str(reserva.id), "intermediacao_status": reserva.intermediacao_status.value}


@router.post("/site/sincronizar")
async def api_sincronizar_site(
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.config.editar"))
    ],
) -> dict:
    return await IntermediacaoService(session).sincronizar_catalogo_site(user.tenant_id)


@router.get("/veiculos-site")
async def api_veiculos_site(
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("intermediacao.config.visualizar"))
    ],
    filial_id: uuid.UUID | None = None,
    categoria_id: uuid.UUID | None = None,
) -> list[dict]:
    return await IntermediacaoService(session).list_veiculos_site(
        user.tenant_id, filial_id=filial_id, categoria_id=categoria_id
    )
