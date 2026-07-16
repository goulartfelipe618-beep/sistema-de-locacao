"""Rotas Web do módulo Automações (§13)."""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.automacoes.schemas import (
    RegraCreate,
    WorkflowCreate,
    WorkflowDecisaoInput,
    WorkflowEtapaInput,
    WorkflowInstanciaCreate,
)
from app.modules.automacoes.service import (
    BeatAdminService,
    ExecucaoService,
    RegraService,
    WorkflowService,
)
from app.modules.identity.service import AuthenticatedUser
from app.shared.enums import (
    AutoAcaoTipo,
    AutoEventoGatilho,
    AutoExecucaoTipo,
    AutoWorkflowTimeoutAcao,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

_EVENTOS = list(AutoEventoGatilho)
_ACOES = list(AutoAcaoTipo)


@router.get("/automacoes/regras", response_class=HTMLResponse)
async def regras_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.regras.visualizar"))
    ],
) -> Any:
    regras = await RegraService(session).list_items(PageParams(page=1, size=100))
    return render(
        request,
        "automacoes/regras_list.html",
        {"title": "Regras de Automação", "regras": regras.items, "eventos": _EVENTOS, "acoes": _ACOES},
    )


@router.post("/automacoes/regras/novo")
async def regra_novo(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.regras.criar"))
    ],
    nome: Annotated[str, Form()],
    evento_gatilho: Annotated[str, Form()],
    acao_tipo: Annotated[str, Form()],
    condicao_json: Annotated[str, Form()] = "{}",
    acao_params_json: Annotated[str, Form()] = "{}",
    prioridade: Annotated[int, Form()] = 100,
):
    data = RegraCreate(
        nome=nome,
        evento_gatilho=AutoEventoGatilho(evento_gatilho),
        acao_tipo=AutoAcaoTipo(acao_tipo),
        condicao_json=json.loads(condicao_json or "{}"),
        acao_params_json=json.loads(acao_params_json or "{}"),
        prioridade=prioridade,
    )
    await RegraService(session).create(current_user.tenant_id, data)
    return RedirectResponse("/automacoes/regras", status_code=303)


@router.post("/automacoes/regras/{regra_id}/executar")
async def regra_executar(
    regra_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.regras.executar"))
    ],
):
    await RegraService(session).executar_manual(current_user.tenant_id, regra_id, {})
    return RedirectResponse("/automacoes/historico", status_code=303)


@router.get("/automacoes/workflows", response_class=HTMLResponse)
async def workflows_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.workflows.visualizar"))
    ],
) -> Any:
    workflows = await WorkflowService(session).list_items(PageParams(page=1, size=100))
    instancias = await WorkflowService(session).list_instancias(PageParams(page=1, size=30))
    return render(
        request,
        "automacoes/workflows_list.html",
        {
            "title": "Workflows",
            "workflows": workflows.items,
            "instancias": instancias.items,
            "timeout_acoes": list(AutoWorkflowTimeoutAcao),
        },
    )


@router.post("/automacoes/workflows/novo")
async def workflow_novo(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.workflows.criar"))
    ],
    codigo: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    etapa_nome: Annotated[str, Form()] = "Aprovação",
    aprovador_papel_slug: Annotated[str, Form()] = "gerente-filial",
):
    data = WorkflowCreate(
        codigo=codigo,
        nome=nome,
        etapas=[
            WorkflowEtapaInput(
                ordem=1,
                nome=etapa_nome,
                aprovador_papel_slug=aprovador_papel_slug or None,
                sla_horas=24,
            )
        ],
    )
    await WorkflowService(session).create(current_user.tenant_id, data)
    return RedirectResponse("/automacoes/workflows", status_code=303)


@router.post("/automacoes/workflows/instancias/{instancia_id}/aprovar")
async def workflow_aprovar(
    instancia_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.workflows.executar"))
    ],
):
    await WorkflowService(session).decidir(
        instancia_id, current_user.id, WorkflowDecisaoInput(aprovar=True)
    )
    return RedirectResponse("/automacoes/workflows", status_code=303)


@router.post("/automacoes/workflows/instancias/{instancia_id}/rejeitar")
async def workflow_rejeitar(
    instancia_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.workflows.executar"))
    ],
):
    await WorkflowService(session).decidir(
        instancia_id, current_user.id, WorkflowDecisaoInput(aprovar=False)
    )
    return RedirectResponse("/automacoes/workflows", status_code=303)


@router.get("/automacoes/agendamentos", response_class=HTMLResponse)
async def agendamentos_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.agendamentos.visualizar"))
    ],
) -> Any:
    svc = BeatAdminService(session)
    jobs = []
    for job in svc.catalogo():
        ultima = await svc.ultima_execucao(current_user.tenant_id, job["key"])
        jobs.append({**job, "ultima": ultima})
    return render(
        request,
        "automacoes/agendamentos_list.html",
        {"title": "Agendamentos (Celery Beat)", "jobs": jobs},
    )


@router.post("/automacoes/agendamentos/{job_key}/disparar")
async def agendamento_disparar(
    job_key: str,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.agendamentos.executar"))
    ],
):
    await BeatAdminService(session).disparar(current_user.tenant_id, job_key)
    return RedirectResponse("/automacoes/agendamentos", status_code=303)


@router.get("/automacoes/historico", response_class=HTMLResponse)
async def historico_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("automacoes.historico.visualizar"))
    ],
    tipo: str = "",
    page: int = 1,
) -> Any:
    t = AutoExecucaoTipo(tipo) if tipo else None
    result = await ExecucaoService(session).list_items(PageParams(page=page, size=50), tipo=t)
    return render(
        request,
        "automacoes/historico.html",
        {
            "title": "Histórico de Automações",
            "execucoes": result.items,
            "page": result.page,
            "pages": result.pages,
            "tipo": tipo,
            "tipos": list(AutoExecucaoTipo),
        },
    )
