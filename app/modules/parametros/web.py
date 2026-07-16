"""Rotas Web do módulo Parâmetros (§14.5)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.identity.service import AuthenticatedUser
from app.modules.parametros.catalog import CATEGORIA_LABELS
from app.modules.parametros.service import ParametroService
from app.modules.tenants.service import FilialService
from app.shared.enums import ParametroCategoria, ParametroTipo

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/configuracoes/parametros", response_class=HTMLResponse)
async def parametros_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.parametro.visualizar"))
    ],
    filial_id: uuid.UUID | None = None,
    categoria: ParametroCategoria | None = None,
) -> Any:
    svc = ParametroService(session)
    parametros = await svc.list_resolved(current_user.tenant_id, filial_id=filial_id, categoria=categoria)
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    can_edit = (
        current_user.is_superuser
        or "configuracoes.parametro.editar" in current_user.permissions
    )
    grouped: dict[str, list] = {}
    for param in parametros:
        label = CATEGORIA_LABELS.get(param.categoria, param.categoria.value)
        grouped.setdefault(label, []).append(param)
    return render(
        request,
        "parametros/list.html",
        {
            "title": "Parâmetros do Sistema",
            "grouped": grouped,
            "filiais": filiais.items,
            "filial_id": filial_id,
            "categoria": categoria,
            "categorias": svc.list_categorias(),
            "categoria_labels": CATEGORIA_LABELS,
            "tipos": list(ParametroTipo),
            "can_edit": can_edit,
            "error": None,
            "success": request.query_params.get("ok"),
        },
    )


@router.post("/configuracoes/parametros")
async def parametros_save(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.parametro.editar"))
    ],
    filial_id: Annotated[str, Form()] = "",
) -> HTMLResponse:
    form = await request.form()
    parsed_filial: uuid.UUID | None = None
    if filial_id.strip():
        parsed_filial = uuid.UUID(filial_id.strip())

    svc = ParametroService(session)
    try:
        for key, value in form.items():
            if not str(key).startswith("param_"):
                continue
            chave = str(key)[6:]
            await svc.set_valor(chave, value, current_user.tenant_id, filial_id=parsed_filial)
    except (AppError, ValueError) as exc:
        await session.rollback()
        parametros = await svc.list_resolved(current_user.tenant_id, filial_id=parsed_filial)
        filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
        grouped: dict[str, list] = {}
        for param in parametros:
            label = CATEGORIA_LABELS.get(param.categoria, param.categoria.value)
            grouped.setdefault(label, []).append(param)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "parametros/list.html",
            {
                "title": "Parâmetros do Sistema",
                "grouped": grouped,
                "filiais": filiais.items,
                "filial_id": parsed_filial,
                "categoria": None,
                "categorias": svc.list_categorias(),
                "categoria_labels": CATEGORIA_LABELS,
                "tipos": list(ParametroTipo),
                "can_edit": True,
                "error": message,
                "success": None,
            },
            status_code=400,
        )

    url = "/configuracoes/parametros?ok=1"
    if parsed_filial:
        url += f"&filial_id={parsed_filial}"
    return RedirectResponse(url=url, status_code=303)
