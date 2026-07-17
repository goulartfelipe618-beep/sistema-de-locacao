"""API REST do módulo Notificações."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.core.deps import ApiSessionDep, require_api_permission
from app.modules.identity.service import AuthenticatedUser
from app.modules.notificacoes.schemas import NotificacaoEnvioRead, NotificacaoRead
from app.modules.notificacoes.service import NotificationService

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
    }


@router.get("/inbox")
async def api_inbox(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("notificacoes.inbox.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await NotificationService(session).list_inbox(current_user.id, page=page, size=size)
    return _page_dict(result, NotificacaoRead)


@router.get("/inbox/nao-lidas")
async def api_count_nao_lidas(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("notificacoes.inbox.visualizar"))
    ],
) -> dict[str, int]:
    total = await NotificationService(session).count_nao_lidas(current_user.id)
    return {"total": total}


@router.post("/inbox/{notificacao_id}/lida", response_model=NotificacaoRead)
async def api_marcar_lida(
    notificacao_id: uuid.UUID,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("notificacoes.inbox.visualizar"))
    ],
) -> NotificacaoRead:
    item = await NotificationService(session).marcar_lida(notificacao_id, current_user.id)
    return NotificacaoRead.model_validate(item)


@router.post("/inbox/marcar-todas-lidas")
async def api_marcar_todas_lidas(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("notificacoes.inbox.visualizar"))
    ],
) -> dict[str, int]:
    total = await NotificationService(session).marcar_todas_lidas(current_user.id)
    return {"marcadas": total}


@router.get("/envios")
async def api_envios(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("notificacoes.envios.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await NotificationService(session).list_envios(page=page, size=size)
    return _page_dict(result, NotificacaoEnvioRead)
