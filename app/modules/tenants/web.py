"""Rotas Web (HTML/Jinja2) do módulo de Empresas/Filiais."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission, require_web_user
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.branding import resolve_logo_url
from app.modules.tenants.schemas import FilialCreate, FilialUpdate, TenantSystemUpdate
from app.modules.tenants.service import FilialService, TenantService
from app.modules.tenants.setup import (
    SETUP_EDIT_PATH,
    SETUP_PATH,
    format_tenant_address,
    is_setup_complete,
    setup_missing_fields,
    sync_tenant_session_flags,
)

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def _can_edit_empresa(user: AuthenticatedUser) -> bool:
    return user.is_superuser or "configuracoes.empresa.editar" in user.permissions


def _sistema_context(
    request: Request,
    tenant,
    *,
    can_edit: bool,
    edit_mode: bool,
    error: str | None = None,
) -> dict:
    setup_mode = not is_setup_complete(tenant)
    return {
        "tenant": tenant,
        "can_edit": can_edit,
        "edit_mode": edit_mode or setup_mode,
        "setup_mode": setup_mode,
        "setup_missing": setup_missing_fields(tenant),
        "logo_preview": resolve_logo_url(tenant),
        "formatted_address": format_tenant_address(tenant),
        "title": "Configurações do Sistema",
        "error": error,
    }


# ================================================================  Sistema (white label)
@router.get("/configuracoes/empresa", response_class=HTMLResponse)
async def company_legacy_redirect() -> RedirectResponse:
    """Compatibilidade: redireciona para configurações do sistema."""
    return RedirectResponse(url=SETUP_PATH, status_code=303)


@router.get("/configuracoes/sistema", response_class=HTMLResponse)
async def sistema_config_view(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.empresa.visualizar"))
    ],
) -> HTMLResponse:
    """Visualização das configurações do sistema (somente leitura)."""
    tenant = await TenantService(session).get_tenant(current_user.tenant_id)
    can_edit = _can_edit_empresa(current_user)
    setup_mode = not is_setup_complete(tenant)
    if setup_mode and can_edit:
        return RedirectResponse(url=SETUP_EDIT_PATH, status_code=303)
    return render(
        request,
        "tenants/sistema_config.html",
        _sistema_context(request, tenant, can_edit=can_edit, edit_mode=False),
    )


@router.get("/configuracoes/sistema/editar", response_class=HTMLResponse)
async def sistema_config_edit(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.empresa.editar"))
    ],
) -> HTMLResponse:
    """Formulário de edição das configurações do sistema."""
    tenant = await TenantService(session).get_tenant(current_user.tenant_id)
    return render(
        request,
        "tenants/sistema_config.html",
        _sistema_context(request, tenant, can_edit=True, edit_mode=True),
    )


@router.get("/configuracoes/sistema/aguardando", response_class=HTMLResponse)
async def sistema_setup_pending(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> HTMLResponse:
    """Informa usuários sem permissão que o administrador ainda não configurou o sistema."""
    tenant = await TenantService(session).get_tenant(current_user.tenant_id)
    if is_setup_complete(tenant):
        return RedirectResponse(url="/", status_code=303)
    return render(
        request,
        "tenants/setup_pending.html",
        {"title": "Configuração pendente", "tenant": tenant},
    )


@router.post("/configuracoes/sistema", response_class=HTMLResponse)
async def sistema_config_save(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("configuracoes.empresa.editar"))
    ],
    legal_name: Annotated[str, Form()],
    trade_name: Annotated[str, Form()] = "",
    app_display_name: Annotated[str, Form()] = "",
    cnpj: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    ie: Annotated[str, Form()] = "",
    website: Annotated[str, Form()] = "",
    document_footer_text: Annotated[str, Form()] = "",
    brand_primary_color: Annotated[str, Form()] = "#1e5a8a",
    logo_url: Annotated[str, Form()] = "",
    zip_code: Annotated[str, Form()] = "",
    address: Annotated[str, Form()] = "",
    number: Annotated[str, Form()] = "",
    complement: Annotated[str, Form()] = "",
    district: Annotated[str, Form()] = "",
    city: Annotated[str, Form()] = "",
    state: Annotated[str, Form()] = "",
    complete_setup: Annotated[str, Form()] = "",
    cert_password: Annotated[str, Form()] = "",
    remove_cert: Annotated[str, Form()] = "",
    logo_file: UploadFile | None = File(None),
    cert_file: UploadFile | None = File(None),
) -> HTMLResponse:
    """Salva configurações do sistema e conclui onboarding quando aplicável."""
    svc = TenantService(session)
    tenant_before = await svc.get_tenant(current_user.tenant_id)
    setup_mode = not is_setup_complete(tenant_before)
    try:
        tenant = tenant_before
        if logo_file and logo_file.filename:
            logo_bytes = await logo_file.read()
            if logo_bytes:
                tenant = await svc.upload_logo(
                    current_user.tenant_id,
                    logo_bytes,
                    logo_file.filename,
                    logo_file.content_type or "image/png",
                )

        data = TenantSystemUpdate(
            legal_name=legal_name,
            trade_name=trade_name or None,
            app_display_name=app_display_name or trade_name or legal_name,
            cnpj=cnpj,
            email=email,
            phone=phone,
            ie=ie or None,
            website=website or None,
            document_footer_text=document_footer_text or None,
            brand_primary_color=brand_primary_color,
            logo_url=logo_url or None,
            zip_code=zip_code,
            address=address,
            number=number,
            complement=complement or None,
            district=district or None,
            city=city,
            state=state,
        )
        tenant = await svc.update_system_config(
            current_user.tenant_id,
            data,
            complete_setup=setup_mode or complete_setup == "on",
        )

        if remove_cert == "on":
            tenant = await svc.update_certificate(
                current_user.tenant_id, pfx_bytes=None, password=None, remove=True
            )
        elif cert_file and cert_file.filename:
            pfx_bytes = await cert_file.read()
            if pfx_bytes:
                tenant = await svc.update_certificate(
                    current_user.tenant_id,
                    pfx_bytes=pfx_bytes,
                    password=cert_password,
                )

        sync_tenant_session_flags(
            request.session,
            tenant,
            can_edit_empresa=True,
        )
        if setup_mode and is_setup_complete(tenant):
            request.session["_flash"] = {
                "type": "success",
                "message": "Configurações concluídas! O sistema está pronto para uso.",
            }
            return RedirectResponse(url="/", status_code=303)
        request.session["_flash"] = {
            "type": "success",
            "message": "Configurações do sistema salvas com sucesso.",
        }
        return RedirectResponse(url=SETUP_PATH, status_code=303)
    except (AppError, ValueError) as exc:
        await session.rollback()
        tenant = await svc.get_tenant(current_user.tenant_id)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "tenants/sistema_config.html",
            _sistema_context(
                request,
                tenant,
                can_edit=True,
                edit_mode=True,
                error=message,
            ),
            status_code=400,
        )


@router.post("/configuracoes/empresa", response_class=HTMLResponse)
async def company_legacy_post_redirect() -> RedirectResponse:
    """Compatibilidade: POST antigo redireciona para a nova rota."""
    return RedirectResponse(url=SETUP_EDIT_PATH, status_code=303)


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
