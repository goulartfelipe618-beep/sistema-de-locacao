"""Rotas Web do Dashboard (página inicial do painel administrativo)."""

from __future__ import annotations

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
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("dashboard.painel.visualizar"))
    ],
) -> HTMLResponse:
    """Renderiza a visão geral com os indicadores do tenant atual."""
    metrics = await DashboardService(session).get_overview()
    return render(
        request,
        "dashboard/home.html",
        {"metrics": metrics, "title": "Visão Geral"},
    )
