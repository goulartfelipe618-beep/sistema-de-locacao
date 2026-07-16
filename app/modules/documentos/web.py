"""Rotas Web do motor de PDF (§16)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission, require_web_user
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.rbac import has_permission
from app.core.templating import render
from app.modules.documentos.catalog import TEMPLATES_BY_ID
from app.modules.documentos.service import ReportService
from app.modules.identity.service import AuthenticatedUser
from app.shared.enums import DocGeradoStatus

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/documentos/historico", response_class=HTMLResponse)
async def documentos_historico(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("documentos.historico.visualizar"))
    ],
    page: int = 1,
) -> HTMLResponse:
    result = await ReportService(session).list_historico(page=page, size=25)
    return render(
        request,
        "documentos/historico.html",
        {"title": "Documentos PDF Gerados", "page_result": result},
    )


@router.get("/documentos/{doc_id}/download")
async def documento_download(
    session: SessionDep,
    doc_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("documentos.historico.visualizar"))
    ],
) -> Response:
    svc = ReportService(session)
    doc = await svc.get(doc_id)
    if doc.status != DocGeradoStatus.CONCLUIDO:
        return Response(status_code=409, content="Documento ainda não está pronto.")

    url = svc.resolve_download_url(doc)
    if url:
        return RedirectResponse(url=url, status_code=302)

    blob = svc.get_inline_bytes(doc)
    if blob is None:
        return Response(status_code=404, content="Arquivo não encontrado.")

    return Response(
        content=blob,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.template_id}.pdf"'},
    )


@router.post("/documentos/emitir/{template_id}/{entidade_id}")
async def documento_emitir(
    session: SessionDep,
    template_id: str,
    entidade_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> RedirectResponse:
    tpl = TEMPLATES_BY_ID.get(template_id)
    if tpl is None:
        raise AppError("Template inválido.", code="invalid_template")

    if not has_permission(
        current_user.permissions,
        tpl.permission,
        is_superuser=current_user.is_superuser,
    ):
        raise AppError("Sem permissão para emitir este documento.", code="forbidden")

    doc = await ReportService(session).gerar_pdf(
        template_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        entidade_id=entidade_id,
    )
    return RedirectResponse(url=f"/documentos/{doc.id}/download", status_code=303)


def pdf_button(template_id: str, entidade_id: uuid.UUID, label: str) -> dict[str, Any]:
    """Helper para templates — formulário de emissão de PDF."""
    return {
        "template_id": template_id,
        "entidade_id": entidade_id,
        "label": label,
        "action": f"/documentos/emitir/{template_id}/{entidade_id}",
    }
