"""Rotas Web do Dashboard (página inicial do painel administrativo)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.templating import render
from app.modules.dashboard.service import DashboardService
from app.modules.identity.service import AuthenticatedUser

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard_home(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("dashboard.painel.visualizar"))
    ],
    filial_id: uuid.UUID | None = None,
) -> HTMLResponse:
    """Renderiza a visão geral com KPIs condicionados às permissões do usuário."""
    filial_param = request.query_params.get("filial_id")
    parsed_filial = uuid.UUID(filial_param) if filial_param else filial_id

    snapshot = await DashboardService(session).get_snapshot(
        permissions=current_user.permissions,
        is_superuser=current_user.is_superuser,
        filial_id=parsed_filial,
    )
    return render(
        request,
        "dashboard/home.html",
        {"snapshot": snapshot, "title": "Visão Geral", "filial_id": parsed_filial},
    )
