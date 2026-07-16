"""API REST do módulo Relatórios."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse

from app.core.deps import ApiSessionDep, require_api_permission
from app.modules.identity.service import AuthenticatedUser
from app.modules.relatorios.catalog import list_by_categoria
from app.modules.relatorios.schemas import AgendamentoCreate, AgendamentoRead, EmissaoCreate, EmissaoRead
from app.modules.relatorios.service import AgendamentoService, EmissaoService
from app.shared.enums import RelCategoria

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@router.get("/catalogo/{categoria}")
async def api_catalogo(
    categoria: RelCategoria,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("relatorios.frota.visualizar")),
    ],
) -> list[dict]:
    return [
        {
            "codigo": r.codigo,
            "titulo": r.titulo,
            "descricao": r.descricao,
            "pesado": r.pesado,
            "suporta_custom": r.suporta_custom,
            "colunas": list(r.colunas_disponiveis),
        }
        for r in list_by_categoria(categoria)
    ]


@router.post("/emitir", response_model=EmissaoRead, status_code=status.HTTP_201_CREATED)
async def api_emitir(
    session: ApiSessionDep,
    payload: EmissaoCreate,
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("relatorios.frota.exportar")),
    ],
) -> EmissaoRead:
    params = dict(payload.parametros)
    if payload.colunas:
        params["colunas"] = payload.colunas
    emissao = await EmissaoService(session).solicitar(
        current_user.tenant_id,
        user_id=current_user.id,
        categoria=payload.categoria,
        relatorio_codigo=payload.relatorio_codigo,
        formato=payload.formato,
        params=params,
        usar_cache=payload.usar_cache,
    )
    return EmissaoRead.model_validate(emissao)


@router.get("/emissoes", response_model=dict)
async def api_list_emissoes(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("relatorios.historico.visualizar")),
    ],
    categoria: RelCategoria | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await EmissaoService(session).list_historico(
        categoria=categoria, page=page, size=size
    )
    return {
        "items": [EmissaoRead.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


@router.get("/emissoes/{emissao_id}", response_model=EmissaoRead)
async def api_get_emissao(
    emissao_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("relatorios.historico.visualizar")),
    ],
) -> EmissaoRead:
    return EmissaoRead.model_validate(await EmissaoService(session).get(emissao_id))


@router.get("/emissoes/{emissao_id}/download")
async def api_download(
    emissao_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("relatorios.historico.visualizar")),
    ],
):
    blob, ct, filename = await EmissaoService(session).get_download(emissao_id)
    return StreamingResponse(
        iter([blob]),
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/agendamentos", response_model=list[AgendamentoRead])
async def api_list_agendamentos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("relatorios.agendamento.visualizar")),
    ],
) -> list[AgendamentoRead]:
    result = await AgendamentoService(session).list_items(size=100)
    return [AgendamentoRead.model_validate(a) for a in result.items]


@router.post("/agendamentos", response_model=AgendamentoRead, status_code=status.HTTP_201_CREATED)
async def api_create_agendamento(
    session: ApiSessionDep,
    payload: AgendamentoCreate,
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_api_permission("relatorios.agendamento.criar")),
    ],
) -> AgendamentoRead:
    item = await AgendamentoService(session).create(
        current_user.tenant_id,
        user_id=current_user.id,
        nome=payload.nome,
        categoria=payload.categoria,
        relatorio_codigo=payload.relatorio_codigo,
        formato=payload.formato,
        parametros=payload.parametros,
        recorrencia=payload.recorrencia,
        hora_execucao=payload.hora_execucao,
        dia_semana=payload.dia_semana,
        dia_mes=payload.dia_mes,
        email_destinatarios=payload.email_destinatarios,
    )
    return AgendamentoRead.model_validate(item)
