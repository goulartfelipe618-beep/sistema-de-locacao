"""Rotas Web (HTML/Jinja2) do módulo de Identidade: login e administração."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import UnitOfWork, get_db_session
from app.core.deps import require_web_user, require_web_permission
from app.core.exceptions import AppError, AuthenticationError
from app.core.pagination import PageParams
from app.core.templating import render
from app.core.ui_theme import persist_ui_theme
from app.modules.identity.repository import RoleRepository, UserRepository
from app.modules.identity.schemas import RoleCreate, RoleUpdate, UserCreate, UserUpdate
from app.modules.identity.service import (
    AuthenticatedUser,
    AuthService,
    RoleService,
    UserService,
)
from app.modules.identity.twofa_service import TwoFactorService
from app.modules.identity.totp import decrypt_recovery_codes
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.service import FilialService
from app.modules.tenants.setup import populate_authenticated_session, post_login_redirect_url

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ==============================================================  Autenticação
@router.get("/login", response_class=HTMLResponse, name="login")
async def login_form(request: Request) -> HTMLResponse:
    """Exibe o formulário de login (ou redireciona se já autenticado)."""
    if request.session.get("user_id"):
        return RedirectResponse(url=post_login_redirect_url(request.session), status_code=303)
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
        user = await AuthService().verify_credentials(
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

    if user.totp_enabled and user.totp_secret_encrypted:
        request.session.clear()
        request.session["pending_2fa_user_id"] = str(user.id)
        request.session["pending_2fa_tenant_id"] = str(user.tenant_id)
        request.session["pending_2fa_exp"] = (
            datetime.now(tz=UTC) + timedelta(minutes=5)
        ).isoformat()
        return render(request, "identity/login_2fa.html", {"error": None})

    await AuthService().finalize_login(
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Resolve a filial padrão do usuário (primeira vinculada, se houver).
    async with UnitOfWork(tenant_id=tenant.id) as uow:
        user_repo = UserRepository(uow.session)
        filial_ids = await user_repo.get_filial_ids(user.id)
        permissions = await user_repo.get_permission_codes(user.id)
        tenant_row = await TenantRepository(uow.session).get(tenant.id)

    request.session.clear()
    populate_authenticated_session(
        request.session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        filial_id=filial_ids[0] if filial_ids else None,
        is_superuser=user.is_superuser,
        tenant=tenant_row or tenant,
        permission_codes=permissions,
    )
    return RedirectResponse(url=post_login_redirect_url(request.session), status_code=303)


@router.get("/login/2fa", response_class=HTMLResponse)
async def login_2fa_form(request: Request) -> HTMLResponse:
    """Exibe formulário do segundo fator."""
    if not request.session.get("pending_2fa_user_id"):
        return RedirectResponse(url="/login", status_code=303)
    return render(request, "identity/login_2fa.html", {"error": None})


@router.post("/login/2fa", response_class=HTMLResponse)
async def login_2fa_submit(
    request: Request,
    code: Annotated[str, Form()],
) -> HTMLResponse:
    """Valida TOTP/recuperação e conclui sessão."""
    user_id_raw = request.session.get("pending_2fa_user_id")
    tenant_id_raw = request.session.get("pending_2fa_tenant_id")
    exp_raw = request.session.get("pending_2fa_exp")
    if not user_id_raw or not tenant_id_raw:
        return RedirectResponse(url="/login", status_code=303)
    if exp_raw:
        try:
            if datetime.fromisoformat(exp_raw) < datetime.now(tz=UTC):
                request.session.clear()
                return render(
                    request,
                    "identity/login.html",
                    {"error": "Sessão 2FA expirada. Faça login novamente.", "email": ""},
                    status_code=401,
                )
        except ValueError:
            pass

    user_id = uuid.UUID(str(user_id_raw))
    tenant_id = uuid.UUID(str(tenant_id_raw))
    auth = AuthService()
    try:
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            user = await TwoFactorService(uow.session).verify_login(
                user_id,
                tenant_id,
                code,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
    except (AuthenticationError, AppError) as exc:
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "identity/login_2fa.html",
            {"error": message},
            status_code=401,
        )

    await auth.finalize_login(
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    async with UnitOfWork(tenant_id=tenant_id) as uow:
        user_repo = UserRepository(uow.session)
        tenant = await TenantRepository(uow.session).get(tenant_id)
        filial_ids = await user_repo.get_filial_ids(user.id)
        permissions = await user_repo.get_permission_codes(user.id)

    request.session.clear()
    populate_authenticated_session(
        request.session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        filial_id=filial_ids[0] if filial_ids else None,
        is_superuser=user.is_superuser,
        tenant=tenant,
        permission_codes=permissions,
    )
    return RedirectResponse(url=post_login_redirect_url(request.session), status_code=303)


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
        {
            "roles": roles,
            "filiais": filiais,
            "selected_roles": [],
            "selected_filiais": [],
            "user": None,
            "error": None,
            "title": "Novo Usuário",
            "action": "/configuracoes/usuarios/novo",
        },
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
        request.session["_flash"] = {"type": "success", "message": "Usuário criado com sucesso."}
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
                "selected_roles": [],
                "selected_filiais": [],
                "user": None,
                "error": message,
                "title": "Novo Usuário",
                "action": "/configuracoes/usuarios/novo",
                "form": {"full_name": full_name, "email": email},
            },
            status_code=400,
        )
    return RedirectResponse(url="/configuracoes/usuarios", status_code=303)


async def _user_form_context(
    session: AsyncSession,
    *,
    user: object | None = None,
    error: str | None = None,
    title: str,
    action: str,
    form: dict | None = None,
) -> dict:
    roles = await RoleRepository(session).list_ordered()
    filiais = await FilialService(session).list_all()
    selected_roles: list[uuid.UUID] = []
    selected_filiais: list[uuid.UUID] = []
    if user is not None:
        repo = UserRepository(session)
        selected_roles = await repo.get_role_ids(user.id)
        selected_filiais = await repo.get_filial_ids(user.id)
    return {
        "user": user,
        "roles": roles,
        "filiais": filiais,
        "selected_roles": selected_roles,
        "selected_filiais": selected_filiais,
        "error": error,
        "title": title,
        "action": action,
        "form": form,
    }


@router.get("/configuracoes/usuarios/{user_id}/editar", response_class=HTMLResponse)
async def user_edit_form(
    user_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.editar"))
    ],
) -> HTMLResponse:
    """Formulário de edição de usuário."""
    target = await UserService(session).get_user(user_id)
    ctx = await _user_form_context(
        session,
        user=target,
        title="Editar Usuário",
        action=f"/configuracoes/usuarios/{user_id}/editar",
    )
    return render(request, "identity/user_form.html", ctx)


@router.post("/configuracoes/usuarios/{user_id}/editar", response_class=HTMLResponse)
async def user_update(
    user_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.editar"))
    ],
    full_name: Annotated[str, Form()],
    password: Annotated[str, Form()] = "",
    is_active: Annotated[bool, Form()] = False,
    role_ids: Annotated[list[str] | None, Form()] = None,
    filial_ids: Annotated[list[str] | None, Form()] = None,
) -> HTMLResponse:
    """Atualiza usuário, papéis e filiais."""
    svc = UserService(session)
    try:
        data = UserUpdate(
            full_name=full_name,
            is_active=is_active,
            password=password or None,
            role_ids=[uuid.UUID(r) for r in (role_ids or [])],
            filial_ids=[uuid.UUID(f) for f in (filial_ids or [])],
        )
        await svc.update_user(user_id, data)
        request.session["_flash"] = {"type": "success", "message": "Usuário atualizado com sucesso."}
    except (AppError, ValueError) as exc:
        await session.rollback()
        target = await svc.get_user(user_id)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        ctx = await _user_form_context(
            session,
            user=target,
            error=message,
            title="Editar Usuário",
            action=f"/configuracoes/usuarios/{user_id}/editar",
            form={"full_name": full_name},
        )
        return render(request, "identity/user_form.html", ctx, status_code=400)
    return RedirectResponse(url="/configuracoes/usuarios", status_code=303)


@router.post("/configuracoes/usuarios/{user_id}/desbloquear")
async def user_unlock(
    user_id: uuid.UUID,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.editar"))
    ],
) -> RedirectResponse:
    """Remove bloqueio temporário do usuário."""
    await UserService(session).unlock_user(user_id)
    return RedirectResponse(url=f"/configuracoes/usuarios/{user_id}/editar", status_code=303)


@router.post("/configuracoes/usuarios/{user_id}/excluir")
async def user_delete(
    request: Request,
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.excluir"))
    ],
) -> RedirectResponse:
    """Remove (soft delete) um usuário."""
    try:
        await UserService(session).delete_user(user_id, actor_id=current_user.id)
        request.session["_flash"] = {"type": "success", "message": "Usuário excluído com sucesso."}
    except AppError as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": exc.message}
    except ValueError as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": str(exc)}
    return RedirectResponse(url="/configuracoes/usuarios", status_code=303)


@router.get("/configuracoes/usuarios/{user_id}/acessos", response_class=HTMLResponse)
async def user_access_log(
    user_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.visualizar"))
    ],
    page: int = 1,
) -> HTMLResponse:
    """Log de acessos (login e falhas) do usuário."""
    svc = UserService(session)
    target = await svc.get_user(user_id)
    result = await svc.list_access_log(user_id, PageParams(page=page, size=25))
    return render(
        request,
        "identity/user_access_log.html",
        {
            "user": target,
            "page_result": result,
            "title": f"Acessos — {target.full_name}",
        },
    )


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
    can_create = (
        _user.is_superuser or "identidade.papel.criar" in _user.permissions
    )
    return render(
        request,
        "identity/roles_list.html",
        {
            "roles": roles,
            "role_perms": role_perms,
            "title": "Papéis e Permissões",
            "can_create": can_create,
            "can_edit": _user.is_superuser or "identidade.papel.editar" in _user.permissions,
            "can_delete": _user.is_superuser or "identidade.papel.excluir" in _user.permissions,
        },
    )


@router.get("/configuracoes/papeis/novo", response_class=HTMLResponse)
async def role_new_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.papel.criar"))
    ],
) -> HTMLResponse:
    """Formulário de criação de papel personalizado."""
    svc = RoleService(session)
    return render(
        request,
        "identity/role_form.html",
        {
            "role": None,
            "permission_groups": await svc.list_permissions_grouped(),
            "selected_permissions": [],
            "error": None,
            "title": "Novo Papel",
            "action": "/configuracoes/papeis/novo",
        },
    )


@router.post("/configuracoes/papeis/novo", response_class=HTMLResponse)
async def role_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.papel.criar"))
    ],
    slug: Annotated[str, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
    permission_ids: Annotated[list[str] | None, Form()] = None,
) -> HTMLResponse:
    """Cria papel personalizado com matriz de permissões."""
    svc = RoleService(session)
    try:
        data = RoleCreate(
            slug=slug.strip().lower(),
            name=name,
            description=description or None,
            permission_ids=[uuid.UUID(p) for p in (permission_ids or [])],
        )
        await svc.create_role(data, tenant_id=current_user.tenant_id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "identity/role_form.html",
            {
                "role": None,
                "permission_groups": await svc.list_permissions_grouped(),
                "selected_permissions": [uuid.UUID(p) for p in (permission_ids or [])],
                "error": message,
                "title": "Novo Papel",
                "action": "/configuracoes/papeis/novo",
                "form": {"slug": slug, "name": name, "description": description},
            },
            status_code=400,
        )
    return RedirectResponse(url="/configuracoes/papeis", status_code=303)


@router.get("/configuracoes/papeis/{role_id}/editar", response_class=HTMLResponse)
async def role_edit_form(
    role_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.papel.editar"))
    ],
) -> HTMLResponse:
    """Formulário de edição de papel e permissões."""
    svc = RoleService(session)
    role = await svc.get_role(role_id)
    return render(
        request,
        "identity/role_form.html",
        {
            "role": role,
            "permission_groups": await svc.list_permissions_grouped(),
            "selected_permissions": await svc.get_permission_ids(role_id),
            "error": None,
            "title": f"Editar Papel — {role.name}",
            "action": f"/configuracoes/papeis/{role_id}/editar",
        },
    )


@router.post("/configuracoes/papeis/{role_id}/editar", response_class=HTMLResponse)
async def role_update(
    role_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.papel.editar"))
    ],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
    permission_ids: Annotated[list[str] | None, Form()] = None,
) -> HTMLResponse:
    """Atualiza papel e matriz de permissões."""
    svc = RoleService(session)
    try:
        data = RoleUpdate(
            name=name,
            description=description or None,
            permission_ids=[uuid.UUID(p) for p in (permission_ids or [])],
        )
        await svc.update_role(role_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        role = await svc.get_role(role_id)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "identity/role_form.html",
            {
                "role": role,
                "permission_groups": await svc.list_permissions_grouped(),
                "selected_permissions": [uuid.UUID(p) for p in (permission_ids or [])],
                "error": message,
                "title": f"Editar Papel — {role.name}",
                "action": f"/configuracoes/papeis/{role_id}/editar",
                "form": {"name": name, "description": description},
            },
            status_code=400,
        )
    return RedirectResponse(url="/configuracoes/papeis", status_code=303)


@router.post("/configuracoes/papeis/{role_id}/excluir")
async def role_delete(
    role_id: uuid.UUID,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.papel.excluir"))
    ],
) -> RedirectResponse:
    """Remove papel personalizado (papéis de sistema são protegidos)."""
    try:
        await RoleService(session).delete_role(role_id)
    except (AppError, ValueError):
        await session.rollback()
    return RedirectResponse(url="/configuracoes/papeis", status_code=303)


# ==============================================================  Perfil (usuário logado)
@router.post("/configuracoes/tema")
async def ui_theme_save(
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
    theme: Annotated[str, Form()],
) -> Response:
    """Persiste preferência de tema (cookie + sessão) para próximos acessos."""
    _ = current_user
    response = Response(status_code=204)
    persist_ui_theme(response, request, theme)
    return response


@router.post("/configuracoes/perfil")
async def profile_update(
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
    full_name: Annotated[str, Form()],
    password: Annotated[str, Form()] = "",
) -> Response:
    """Atualiza nome e senha do usuário logado (modal do cabeçalho)."""
    try:
        data = UserUpdate(
            full_name=full_name.strip(),
            password=password.strip() or None,
        )
        user = await UserService(session).update_user(current_user.id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return Response(
            status_code=422,
            headers={"HX-Trigger": json.dumps({"profileError": {"message": message}})},
        )
    return Response(
        status_code=204,
        headers={
            "HX-Trigger": json.dumps(
                {"profileSaved": {"full_name": user.full_name, "email": user.email}}
            )
        },
    )


# ==============================================================  2FA (§14.3)
@router.get("/configuracoes/seguranca", response_class=HTMLResponse)
async def seguranca_2fa(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> HTMLResponse:
    """Configuração de autenticação em dois fatores do usuário logado."""
    user = await UserService(session).get_user(current_user.id)
    remaining = len(decrypt_recovery_codes(user.recovery_codes_encrypted))
    return render(
        request,
        "identity/twofa_setup.html",
        {
            "title": "Autenticação em Dois Fatores",
            "user": user,
            "recovery_remaining": remaining,
            "setup": None,
            "recovery_codes": None,
            "error": None,
            "success": None,
        },
    )


@router.post("/configuracoes/seguranca/iniciar", response_class=HTMLResponse)
async def seguranca_2fa_iniciar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> HTMLResponse:
    """Gera QR Code para aplicativo autenticador."""
    user = await UserService(session).get_user(current_user.id)
    setup = await TwoFactorService(session).begin_setup(current_user.id)
    return render(
        request,
        "identity/twofa_setup.html",
        {
            "title": "Autenticação em Dois Fatores",
            "user": user,
            "recovery_remaining": 0,
            "setup": setup,
            "recovery_codes": None,
            "error": None,
            "success": None,
        },
    )


@router.post("/configuracoes/seguranca/confirmar", response_class=HTMLResponse)
async def seguranca_2fa_confirmar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
    code: Annotated[str, Form()],
) -> HTMLResponse:
    """Confirma ativação do 2FA."""
    user = await UserService(session).get_user(current_user.id)
    try:
        recovery = await TwoFactorService(session).confirm_setup(current_user.id, code)
    except (AppError, ValueError) as exc:
        setup = await TwoFactorService(session).begin_setup(current_user.id)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "identity/twofa_setup.html",
            {
                "title": "Autenticação em Dois Fatores",
                "user": user,
                "recovery_remaining": 0,
                "setup": setup,
                "recovery_codes": None,
                "error": message,
                "success": None,
            },
            status_code=400,
        )
    user = await UserService(session).get_user(current_user.id)
    return render(
        request,
        "identity/twofa_setup.html",
        {
            "title": "Autenticação em Dois Fatores",
            "user": user,
            "recovery_remaining": len(recovery),
            "setup": None,
            "recovery_codes": recovery,
            "error": None,
            "success": "2FA ativado com sucesso. Guarde os códigos de recuperação.",
        },
    )


@router.post("/configuracoes/seguranca/desativar", response_class=HTMLResponse)
async def seguranca_2fa_desativar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
    password: Annotated[str, Form()],
    code: Annotated[str, Form()],
) -> HTMLResponse:
    """Desativa 2FA."""
    user = await UserService(session).get_user(current_user.id)
    try:
        await TwoFactorService(session).disable(
            current_user.id, password=password, code=code
        )
    except (AppError, ValueError, AuthenticationError) as exc:
        remaining = len(decrypt_recovery_codes(user.recovery_codes_encrypted))
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "identity/twofa_setup.html",
            {
                "title": "Autenticação em Dois Fatores",
                "user": user,
                "recovery_remaining": remaining,
                "setup": None,
                "recovery_codes": None,
                "error": message,
                "success": None,
            },
            status_code=400,
        )
    user = await UserService(session).get_user(current_user.id)
    return render(
        request,
        "identity/twofa_setup.html",
        {
            "title": "Autenticação em Dois Fatores",
            "user": user,
            "recovery_remaining": 0,
            "setup": None,
            "recovery_codes": None,
            "error": None,
            "success": "2FA desativado.",
        },
    )


@router.post("/configuracoes/usuarios/{user_id}/reset-2fa")
async def user_reset_2fa(
    user_id: uuid.UUID,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("identidade.usuario.editar"))
    ],
) -> RedirectResponse:
    """Remove 2FA de um usuário (administrador)."""
    try:
        await TwoFactorService(session).admin_reset(user_id)
    except (AppError, ValueError):
        await session.rollback()
    return RedirectResponse(url=f"/configuracoes/usuarios/{user_id}/editar", status_code=303)
