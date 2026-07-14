"""Rotas Web do módulo de Auditoria (consulta da trilha)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.audit.repository import AuditRepository
from app.modules.identity.service import AuthenticatedUser

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/auditoria/trilha", response_class=HTMLResponse)
async def audit_trail(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("auditoria.trilha.visualizar"))
    ],
    page: int = 1,
    action: str | None = None,
) -> HTMLResponse:
    """Lista a trilha de auditoria do tenant atual, com filtro por ação."""
    result = await AuditRepository(session).paginate(
        PageParams(page=page, size=30),
        tenant_id=current_user.tenant_id,
        action=action,
    )
    return render(
        request,
        "audit/trail.html",
        {"page_result": result, "action": action or "", "title": "Trilha de Auditoria"},
    )
