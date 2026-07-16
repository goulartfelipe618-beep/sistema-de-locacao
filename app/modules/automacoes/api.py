"""API REST do módulo Automações (§13)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.automacoes.schemas import (
    ExecucaoRead,
    RegraCreate,
    RegraRead,
    RegraUpdate,
    WorkflowCreate,
    WorkflowDecisaoInput,
    WorkflowInstanciaCreate,
    WorkflowRead,
)
from app.modules.automacoes.service import (
    BeatAdminService,
    ExecucaoService,
    RegraService,
    WorkflowService,
)
from app.modules.identity.service import AuthenticatedUser
from app.shared.enums import AutoExecucaoTipo

router = APIRouter(prefix="/automacoes", tags=["Automações"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    }


@router.get("/regras")
async def list_regras(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.regras.visualizar"))
    ],
    page: int = Query(1, ge=1),
) -> dict:
    return _page_dict(await RegraService(session).list_items(PageParams(page=page, size=50)), RegraRead)


@router.post("/regras", response_model=RegraRead, status_code=status.HTTP_201_CREATED)
async def create_regra(
    session: ApiSessionDep,
    payload: RegraCreate,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.regras.criar"))
    ],
) -> RegraRead:
    return RegraRead.model_validate(
        await RegraService(session).create(current_user.tenant_id, payload)
    )


@router.patch("/regras/{regra_id}", response_model=RegraRead)
async def update_regra(
    regra_id: uuid.UUID,
    session: ApiSessionDep,
    payload: RegraUpdate,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.regras.editar"))
    ],
) -> RegraRead:
    return RegraRead.model_validate(await RegraService(session).update(regra_id, payload))


@router.post("/regras/{regra_id}/executar", response_model=ExecucaoRead)
async def executar_regra(
    regra_id: uuid.UUID,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.regras.executar"))
    ],
    context: dict = Body(default_factory=dict),
) -> ExecucaoRead:
    execucao = await RegraService(session).executar_manual(
        current_user.tenant_id, regra_id, context
    )
    return ExecucaoRead.model_validate(execucao)


@router.get("/workflows")
async def list_workflows(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.workflows.visualizar"))
    ],
) -> list[WorkflowRead]:
    result = await WorkflowService(session).list_items(PageParams(page=1, size=100))
    return [WorkflowRead.model_validate(w) for w in result.items]


@router.post("/workflows", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    session: ApiSessionDep,
    payload: WorkflowCreate,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.workflows.criar"))
    ],
) -> WorkflowRead:
    return WorkflowRead.model_validate(
        await WorkflowService(session).create(current_user.tenant_id, payload)
    )


@router.post("/workflows/iniciar")
async def iniciar_workflow(
    session: ApiSessionDep,
    payload: WorkflowInstanciaCreate,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.workflows.executar"))
    ],
) -> dict:
    inst = await WorkflowService(session).iniciar(current_user.tenant_id, payload)
    return {"id": str(inst.id), "status": inst.status.value}


@router.post("/workflows/instancias/{instancia_id}/decidir")
async def decidir_workflow(
    instancia_id: uuid.UUID,
    session: ApiSessionDep,
    payload: WorkflowDecisaoInput,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.workflows.executar"))
    ],
) -> dict:
    inst = await WorkflowService(session).decidir(instancia_id, current_user.id, payload)
    return {"id": str(inst.id), "status": inst.status.value}


@router.get("/beat")
async def list_beat(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.agendamentos.visualizar"))
    ],
) -> list[dict]:
    svc = BeatAdminService(session)
    jobs = svc.catalogo()
    out = []
    for job in jobs:
        ultima = await svc.ultima_execucao(current_user.tenant_id, job["key"])
        out.append(
            {
                **job,
                "ultima_execucao": ultima.concluido_em.isoformat() if ultima and ultima.concluido_em else None,
                "ultimo_status": ultima.status.value if ultima else None,
            }
        )
    return out


@router.post("/beat/{job_key}/disparar", response_model=ExecucaoRead)
async def disparar_beat(
    job_key: str,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.agendamentos.executar"))
    ],
) -> ExecucaoRead:
    execucao = await BeatAdminService(session).disparar(current_user.tenant_id, job_key)
    return ExecucaoRead.model_validate(execucao)


@router.get("/historico")
async def historico(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("automacoes.historico.visualizar"))
    ],
    tipo: AutoExecucaoTipo | None = None,
    page: int = Query(1, ge=1),
) -> dict:
    result = await ExecucaoService(session).list_items(
        PageParams(page=page, size=50), tipo=tipo
    )
    return _page_dict(result, ExecucaoRead)
