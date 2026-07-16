"""Rotas API do motor de PDF (§16)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import ApiSessionDep, get_current_api_user, require_api_permission
from app.core.exceptions import NotFoundError
from app.core.pagination import PagedResponse, PageMeta, PageParams
from app.core.rbac import has_permission
from app.modules.documentos.catalog import TEMPLATES_BY_ID
from app.modules.documentos.schemas import DocumentoGeradoRead, GerarPdfRequest
from app.modules.documentos.service import ReportService
from app.modules.identity.service import AuthenticatedUser

router = APIRouter(prefix="/documentos", tags=["Documentos PDF"])

ViewDep = Annotated[
    AuthenticatedUser, Depends(require_api_permission("documentos.historico.visualizar"))
]


@router.get("", response_model=PagedResponse[DocumentoGeradoRead])
async def list_documentos(
    session: ApiSessionDep,
    current_user: ViewDep,
    page: int = 1,
    size: int = 25,
) -> PagedResponse[DocumentoGeradoRead]:
    result = await ReportService(session).list_historico(page=page, size=size)
    return PagedResponse(
        items=[DocumentoGeradoRead.model_validate(i) for i in result.items],
        meta=PageMeta(
            page=result.page,
            size=result.size,
            total=result.total,
            pages=result.pages,
        ),
    )


@router.get("/{doc_id}", response_model=DocumentoGeradoRead)
async def get_documento(
    doc_id: uuid.UUID,
    session: ApiSessionDep,
    current_user: ViewDep,
) -> DocumentoGeradoRead:
    doc = await ReportService(session).get(doc_id)
    return DocumentoGeradoRead.model_validate(doc)


@router.post("/gerar", response_model=DocumentoGeradoRead)
async def gerar_documento(
    payload: GerarPdfRequest,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_api_user)],
) -> DocumentoGeradoRead:
    tpl = TEMPLATES_BY_ID.get(payload.template_id)
    if tpl is None:
        raise NotFoundError("Template não encontrado.")
    if not has_permission(
        current_user.permissions,
        tpl.permission,
        is_superuser=current_user.is_superuser,
    ):
        raise NotFoundError("Sem permissão para este documento.")

    doc = await ReportService(session).gerar_pdf(
        payload.template_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        entidade_id=payload.entidade_id,
        filial_id=payload.filial_id,
        sincrono=payload.sincrono,
        extra=payload.extra,
    )
    return DocumentoGeradoRead.model_validate(doc)
