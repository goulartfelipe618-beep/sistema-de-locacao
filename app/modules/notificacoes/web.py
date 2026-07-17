"""Rotas Web do módulo Notificações."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.identity.service import AuthenticatedUser
from app.modules.notificacoes.service import NotificationService

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/notificacoes", response_class=HTMLResponse)
async def inbox_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("notificacoes.inbox.visualizar"))
    ],
) -> Any:
    page = await NotificationService(session).list_inbox(
        current_user.id, page=1, size=50
    )
    nao_lidas = await NotificationService(session).count_nao_lidas(current_user.id)
    return render(
        request,
        "notificacoes/inbox.html",
        {
            "title": "Notificações",
            "notificacoes": page.items,
            "nao_lidas": nao_lidas,
        },
    )


@router.post("/notificacoes/{notificacao_id}/lida")
async def inbox_marcar_lida(
    session: SessionDep,
    notificacao_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("notificacoes.inbox.visualizar"))
    ],
) -> RedirectResponse:
    await NotificationService(session).marcar_lida(notificacao_id, current_user.id)
    return RedirectResponse(url="/notificacoes", status_code=303)


@router.post("/notificacoes/marcar-todas-lidas")
async def inbox_marcar_todas(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("notificacoes.inbox.visualizar"))
    ],
) -> RedirectResponse:
    await NotificationService(session).marcar_todas_lidas(current_user.id)
    return RedirectResponse(url="/notificacoes", status_code=303)


@router.get("/notificacoes/envios", response_class=HTMLResponse)
async def envios_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("notificacoes.envios.visualizar"))
    ],
) -> Any:
    envios = await NotificationService(session).list_envios(
        page=1, size=100
    )
    return render(
        request,
        "notificacoes/envios.html",
        {"title": "Histórico de Envios", "envios": envios.items},
    )
