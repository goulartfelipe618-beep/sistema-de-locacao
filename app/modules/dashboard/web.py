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
from app.modules.tenants.service import FilialService
from app.shared.query_params import parse_optional_uuid
from app.web.sectors import build_quick_links, resolve_primary_sector

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard_home(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("dashboard.painel.visualizar"))
    ],
) -> HTMLResponse:
    """Renderiza a visão geral com KPIs condicionados às permissões do usuário."""
    parsed_filial = parse_optional_uuid(request.query_params.get("filial_id"))

    snapshot, materialized_at = await DashboardService(session).get_snapshot(
        permissions=current_user.permissions,
        is_superuser=current_user.is_superuser,
        filial_id=parsed_filial,
        tenant_id=current_user.tenant_id,
    )
    filiais = await FilialService(session).list_all()
    sector = resolve_primary_sector(current_user)
    return render(
        request,
        "dashboard/home.html",
        {
            "snapshot": snapshot,
            "title": "Visão Geral",
            "filial_id": parsed_filial,
            "filiais": filiais,
            "materialized_at": materialized_at,
            "sector": sector,
            "quick_links": build_quick_links(current_user),
        },
    )
