"""Rotas Web (HTML/Jinja2) do módulo de Empresas/Filiais."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.branding import resolve_logo_url
from app.modules.tenants.schemas import FilialCreate, FilialUpdate, TenantUpdate
from app.modules.tenants.service import FilialService, TenantService

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ================================================================  Empresa
@router.get("/configuracoes/empresa", response_class=HTMLResponse)
async def company_view(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.empresa.visualizar"))
    ],
) -> HTMLResponse:
    """Exibe os dados cadastrais da empresa (tenant)."""
    tenant = await TenantService(session).get_tenant(current_user.tenant_id)
    can_edit = (
        current_user.is_superuser
        or "configuracoes.empresa.editar" in current_user.permissions
    )
    return render(
        request,
        "tenants/company.html",
        {
            "tenant": tenant,
            "can_edit": can_edit,
            "title": "Dados da Empresa",
            "error": None,
            "logo_preview": resolve_logo_url(tenant),
        },
    )


@router.post("/configuracoes/empresa", response_class=HTMLResponse)
async def company_update(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.empresa.editar"))
    ],
    legal_name: Annotated[str, Form()],
    trade_name: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    logo_url: Annotated[str, Form()] = "",
    logo_storage_key: Annotated[str, Form()] = "",
    brand_primary_color: Annotated[str, Form()] = "#1e5a8a",
    cert_password: Annotated[str, Form()] = "",
    remove_cert: Annotated[str, Form()] = "",
    cert_file: UploadFile | None = File(None),
) -> HTMLResponse:
    """Atualiza os dados cadastrais, branding e certificado da empresa."""
    svc = TenantService(session)
    try:
        data = TenantUpdate(
            legal_name=legal_name,
            trade_name=trade_name or None,
            email=email or None,
            phone=phone or None,
            logo_url=logo_url or None,
            logo_storage_key=logo_storage_key or None,
            brand_primary_color=brand_primary_color or None,
        )
        tenant = await svc.update_tenant(current_user.tenant_id, data)

        if remove_cert == "on":
            tenant = await svc.update_certificate(current_user.tenant_id, pfx_bytes=None, password=None, remove=True)
        elif cert_file and cert_file.filename:
            pfx_bytes = await cert_file.read()
            if pfx_bytes:
                tenant = await svc.update_certificate(
                    current_user.tenant_id,
                    pfx_bytes=pfx_bytes,
                    password=cert_password,
                )

        request.session["tenant_branding"] = svc.session_branding(tenant)
    except (AppError, ValueError) as exc:
        await session.rollback()
        tenant = await svc.get_tenant(current_user.tenant_id)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "tenants/company.html",
            {
                "tenant": tenant,
                "can_edit": True,
                "title": "Dados da Empresa",
                "error": message,
                "logo_preview": resolve_logo_url(tenant),
            },
            status_code=400,
        )
    return RedirectResponse(url="/configuracoes/empresa", status_code=303)


# ================================================================  Filiais
@router.get("/configuracoes/filiais", response_class=HTMLResponse)
async def filiais_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.filial.visualizar"))
    ],
    page: int = 1,
) -> HTMLResponse:
    """Lista de filiais/unidades."""
    result = await FilialService(session).list_filiais(PageParams(page=page, size=25))
    return render(
        request,
        "tenants/filiais_list.html",
        {"page_result": result, "title": "Filiais / Unidades"},
    )


@router.get("/configuracoes/filiais/nova", response_class=HTMLResponse)
async def filial_new_form(
    request: Request,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.filial.criar"))
    ],
) -> HTMLResponse:
    """Formulário de criação de filial."""
    return render(
        request,
        "tenants/filial_form.html",
        {
            "filial": None,
            "error": None,
            "title": "Nova Filial",
            "action": "/configuracoes/filiais/nova",
        },
    )


@router.post("/configuracoes/filiais/nova", response_class=HTMLResponse)
async def filial_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.filial.criar"))
    ],
    code: Annotated[str, Form()],
    name: Annotated[str, Form()],
    cnpj: Annotated[str, Form()] = "",
    city: Annotated[str, Form()] = "",
    state: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    is_headquarters: Annotated[bool, Form()] = False,
) -> HTMLResponse:
    """Cria uma nova filial."""
    try:
        data = FilialCreate(
            code=code,
            name=name,
            cnpj=cnpj or None,
            city=city or None,
            state=state or None,
            phone=phone or None,
            is_headquarters=is_headquarters,
        )
        await FilialService(session).create_filial(data, tenant_id=current_user.tenant_id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "tenants/filial_form.html",
            {
                "filial": None,
                "error": message,
                "title": "Nova Filial",
                "action": "/configuracoes/filiais/nova",
                "form": {"code": code, "name": name},
            },
            status_code=400,
        )
    return RedirectResponse(url="/configuracoes/filiais", status_code=303)



@router.get("/configuracoes/filiais/{filial_id}/editar", response_class=HTMLResponse)
async def filial_edit_form(
    filial_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.filial.editar"))
    ],
) -> HTMLResponse:
    """Formulário de edição de filial."""
    filial = await FilialService(session).get_filial(filial_id)
    return render(
        request,
        "tenants/filial_form.html",
        {
            "filial": filial,
            "error": None,
            "title": "Editar Filial",
            "action": f"/configuracoes/filiais/{filial_id}/editar",
        },
    )


@router.post("/configuracoes/filiais/{filial_id}/editar", response_class=HTMLResponse)
async def filial_update(
    filial_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.filial.editar"))
    ],
    name: Annotated[str, Form()],
    city: Annotated[str, Form()] = "",
    state: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    is_headquarters: Annotated[bool, Form()] = False,
) -> HTMLResponse:
    """Atualiza uma filial existente."""
    try:
        data = FilialUpdate(
            name=name,
            city=city or None,
            state=state or None,
            phone=phone or None,
            is_headquarters=is_headquarters,
        )
        await FilialService(session).update_filial(filial_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        filial = await FilialService(session).get_filial(filial_id)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "tenants/filial_form.html",
            {
                "filial": filial,
                "error": message,
                "title": "Editar Filial",
                "action": f"/configuracoes/filiais/{filial_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse(url="/configuracoes/filiais", status_code=303)
