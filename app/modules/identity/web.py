"""Rotas Web (HTML/Jinja2) do módulo de Identidade: login e administração."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import UnitOfWork, get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError, AuthenticationError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.identity.repository import RoleRepository, UserRepository
from app.modules.identity.schemas import UserCreate
from app.modules.identity.service import AuthenticatedUser, AuthService, UserService
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.service import FilialService

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ==============================================================  Autenticação
@router.get("/login", response_class=HTMLResponse, name="login")
async def login_form(request: Request) -> HTMLResponse:
    """Exibe o formulário de login (ou redireciona se já autenticado)."""
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    return render(request, "identity/login.html", {"error": None, "email": ""})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> HTMLResponse:
    """Processa o login: autentica, cria a sessão e redireciona ao dashboard."""
    slug = settings.default_tenant_slug
    async with UnitOfWork(tenant_id=None) as uow:
        tenant = await TenantRepository(uow.session).get_by_slug(slug)

    if tenant is None:
        return render(
            request,
            "identity/login.html",
            {"error": "Empresa não configurada. Execute o seed inicial.", "email": email},
            status_code=400,
        )

    try:
        user = await AuthService().authenticate(
            tenant_id=tenant.id,
            email=email,
            password=password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthenticationError as exc:
        return render(
            request,
            "identity/login.html",
            {"error": exc.message, "email": email},
            status_code=401,
        )

    # Resolve a filial padrão do usuário (primeira vinculada, se houver).
    async with UnitOfWork(tenant_id=tenant.id) as uow:
        filial_ids = await UserRepository(uow.session).get_filial_ids(user.id)

    request.session.clear()
    request.session["user_id"] = str(user.id)
    request.session["tenant_id"] = str(user.tenant_id)
    request.session["filial_id"] = str(filial_ids[0]) if filial_ids else None
    request.session["is_superuser"] = user.is_superuser
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout", name="logout")
async def logout(request: Request) -> RedirectResponse:
    """Encerra a sessão do usuário (somente POST, evita CSRF via GET)."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
async def logout_get() -> RedirectResponse:
    """Compatibilidade: GET redireciona ao login sem encerrar sessão por CSRF."""
    return RedirectResponse(url="/login", status_code=303)


# ==============================================================  Usuários (UI)
@router.get("/configuracoes/usuarios", response_class=HTMLResponse)
async def users_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.visualizar"))
    ],
    page: int = 1,
    search: str | None = None,
) -> HTMLResponse:
    """Lista de usuários com busca e paginação."""
    result = await UserService(session).list_users(PageParams(page=page, size=25), search=search)
    return render(
        request,
        "identity/users_list.html",
        {"page_result": result, "search": search or "", "title": "Usuários"},
    )


@router.get("/configuracoes/usuarios/novo", response_class=HTMLResponse)
async def user_new_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.criar"))
    ],
) -> HTMLResponse:
    """Formulário de criação de usuário."""
    roles = await RoleRepository(session).list_ordered()
    filiais = await FilialService(session).list_all()
    return render(
        request,
        "identity/user_form.html",
        {"roles": roles, "filiais": filiais, "error": None, "title": "Novo Usuário"},
    )


@router.post("/configuracoes/usuarios/novo", response_class=HTMLResponse)
async def user_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.criar"))
    ],
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    is_active: Annotated[bool, Form()] = False,
    role_ids: Annotated[list[str] | None, Form()] = None,
    filial_ids: Annotated[list[str] | None, Form()] = None,
) -> HTMLResponse:
    """Cria um usuário a partir do formulário administrativo."""
    try:
        data = UserCreate(
            full_name=full_name,
            email=email,
            password=password,
            is_active=is_active,
            role_ids=[uuid.UUID(r) for r in (role_ids or [])],
            filial_ids=[uuid.UUID(f) for f in (filial_ids or [])],
        )
        await UserService(session).create_user(data, tenant_id=current_user.tenant_id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        roles = await RoleRepository(session).list_ordered()
        filiais = await FilialService(session).list_all()
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "identity/user_form.html",
            {
                "roles": roles,
                "filiais": filiais,
                "error": message,
                "title": "Novo Usuário",
                "form": {"full_name": full_name, "email": email},
            },
            status_code=400,
        )
    return RedirectResponse(url="/configuracoes/usuarios", status_code=303)


# ==============================================================  Papéis (UI)
@router.get("/configuracoes/papeis", response_class=HTMLResponse)
async def roles_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.papel.visualizar"))
    ],
) -> HTMLResponse:
    """Lista de papéis (roles) e suas descrições."""
    roles = await RoleRepository(session).list_ordered()
    from sqlalchemy import func, select

    from app.modules.identity.models import RolePermission

    counts = dict(
        (
            await session.execute(
                select(RolePermission.role_id, func.count())
                .group_by(RolePermission.role_id)
            )
        ).all()
    )
    role_perms = {role.id: int(counts.get(role.id, 0)) for role in roles}
    return render(
        request,
        "identity/roles_list.html",
        {"roles": roles, "role_perms": role_perms, "title": "Papéis e Permissões"},
    )
