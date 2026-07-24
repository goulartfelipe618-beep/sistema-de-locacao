"""Rotas Web do módulo Integrações (§12)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from pydantic import ValidationError
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import require_web_permission, require_web_user
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.rbac import has_permission
from app.core.templating import render
from app.modules.cadastros.service import ClienteService
from app.modules.cadastros.service_extra import MotoristaService
from app.modules.frota.service import VeiculoService
from app.modules.identity.service import AuthenticatedUser
from app.modules.integracoes.adapters.registry import PROVEDORES_POR_TIPO
from app.modules.integracoes.schemas import (
    ApiKeyCreate,
    CreditoConsultaInput,
    ProvedorConfigCreate,
    TransitoCnhInput,
    TransitoDebitosInput,
    TransitoMultasInput,
)
from app.modules.integracoes.outbound import OUTBOUND_EVENTOS, OutboundWebhookService
from app.modules.integracoes.site_atendimento import SiteAtendimentoService, build_atendimento_webhook_url
from app.modules.integracoes.service import (
    ApiKeyService,
    CreditoService,
    ProvedorConfigService,
    TelemetriaIntegracaoService,
    TransitoService,
    WebhookLogService,
)
from app.modules.integracoes.site_slides import SiteSlideService, resolve_slide_image_url
from app.modules.tenants.schemas import SiteThemeUpdate
from app.modules.tenants.service import FilialService, TenantService
from app.modules.tenants.site_transition import site_transition_payload, tenant_has_transition_image
from app.shared.enums import IntegracaoTipo

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

_CREATE_PERMS: dict[str, str] = {
    "pagamentos": "integracoes.pagamentos.criar",
    "transito": "integracoes.transito.criar",
    "credito": "integracoes.credito.criar",
    "telemetria": "integracoes.telemetria.criar",
}

_EDIT_PERMS: dict[str, str] = {
    "pagamentos": "integracoes.pagamentos.editar",
    "transito": "integracoes.transito.editar",
    "credito": "integracoes.credito.editar",
    "telemetria": "integracoes.telemetria.editar",
}

API_PUBLIC_SCOPES: list[tuple[str, str]] = [
    ("catalogo:read", "Empresa, filiais, grupos de veículos e slides do site"),
    ("disponibilidade:read", "Consultar disponibilidade"),
    ("veiculos:read", "Listar veículos publicados no site"),
    ("pricing:read", "Cotação de preços (canal site)"),
    ("reservas:write", "Criar reservas"),
    ("contratos:read", "Consultar contratos"),
]


def _can_manage_config(user: AuthenticatedUser, tipo: str, *, edit: bool = False) -> bool:
    perm_map = _EDIT_PERMS if edit else _CREATE_PERMS
    perm = perm_map.get(tipo, "integracoes.pagamentos.criar")
    return has_permission(user.permissions, perm, is_superuser=user.is_superuser)


async def _filiais(session: AsyncSession) -> list:
    return (await FilialService(session).list_filiais(PageParams(page=1, size=100))).items


async def _render_hub(
    request: Request,
    session: AsyncSession,
    *,
    title: str,
    tipo: IntegracaoTipo,
    extra: dict | None = None,
) -> Any:
    configs = await ProvedorConfigService(session).list_items(
        PageParams(page=1, size=50), tipo=tipo
    )
    ctx: dict[str, Any] = {
        "title": title,
        "tipo": tipo,
        "configs": configs.items,
        "filiais": await _filiais(session),
        "tenant_slug": settings.default_tenant_slug,
        "provedores": PROVEDORES_POR_TIPO.get(tipo.value, ("simulador",)),
        "test_flash": request.query_params.get("test"),
        "test_config": request.query_params.get("config"),
    }
    webhooks = None
    if tipo == IntegracaoTipo.PAGAMENTOS:
        webhooks = await WebhookLogService(session).list_items(PageParams(page=1, size=20))
        ctx["webhooks"] = webhooks.items
    if extra:
        ctx.update(extra)
    template = "integracoes/transito.html" if tipo == IntegracaoTipo.TRANSITO else (
        "integracoes/credito.html" if tipo == IntegracaoTipo.CREDITO else "integracoes/hub.html"
    )
    return render(request, template, ctx)


@router.get("/integracoes/pagamentos", response_class=HTMLResponse)
async def pagamentos_hub(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.pagamentos.visualizar"))
    ],
) -> Any:
    return await _render_hub(request, session, title="Pagamentos", tipo=IntegracaoTipo.PAGAMENTOS)


@router.get("/integracoes/transito", response_class=HTMLResponse)
async def transito_hub(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.transito.visualizar"))
    ],
) -> Any:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    motoristas = await MotoristaService(session).list_items(PageParams(page=1, size=200))
    consultas = await TransitoService(session).list_consultas(PageParams(page=1, size=20))
    return await _render_hub(
        request,
        session,
        title="Trânsito (DETRAN)",
        tipo=IntegracaoTipo.TRANSITO,
        extra={
            "veiculos": veiculos.items,
            "motoristas": motoristas.items,
            "consultas": consultas.items,
        },
    )


@router.get("/integracoes/credito", response_class=HTMLResponse)
async def credito_hub(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.credito.visualizar"))
    ],
) -> Any:
    clientes = await ClienteService(session).list_clientes(PageParams(page=1, size=200))
    return await _render_hub(
        request,
        session,
        title="Crédito",
        tipo=IntegracaoTipo.CREDITO,
        extra={"clientes": clientes.items},
    )


@router.get("/integracoes/telemetria", response_class=HTMLResponse)
async def telemetria_hub(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.telemetria.visualizar"))
    ],
) -> Any:
    return await _render_hub(request, session, title="Telemetria", tipo=IntegracaoTipo.TELEMETRIA)


@router.get("/integracoes/api", response_class=HTMLResponse)
async def api_publica_hub(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.visualizar"))
    ],
) -> Any:
    svc = ApiKeyService(session)
    keys_page = await svc.list_items(PageParams(page=1, size=50))
    key_rows = [
        {"key": k, "scopes": sorted(svc.scopes(k))}
        for k in keys_page.items
    ]
    webhooks = await OutboundWebhookService(session).list_items(PageParams(page=1, size=50))
    atendimento_token = await SiteAtendimentoService(session).ensure_token(current_user.tenant_id)
    await session.commit()
    base_url = str(request.base_url).rstrip("/")
    atendimento_webhook_url = build_atendimento_webhook_url(base_url, atendimento_token)
    return render(
        request,
        "integracoes/api_publica.html",
        {
            "title": "API Pública",
            "key_rows": key_rows,
            "webhooks": webhooks.items,
            "outbound_eventos": OUTBOUND_EVENTOS,
            "api_scopes": API_PUBLIC_SCOPES,
            "docs_url": "/docs",
            "openapi_url": "/openapi.json",
            "atendimento_webhook_url": atendimento_webhook_url,
            "atendimento_env_var": "SITE_ATENDIMENTO_WEBHOOK_URL",
        },
    )


@router.post("/integracoes/configs/novo")
async def config_novo(
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
    tipo: Annotated[str, Form()],
    provedor: Annotated[str, Form()] = "simulador",
    nome: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    client_id: Annotated[str, Form()] = "",
    client_secret: Annotated[str, Form()] = "",
    api_key: Annotated[str, Form()] = "",
    base_url: Annotated[str, Form()] = "",
    webhook_secret: Annotated[str, Form()] = "",
):
    if not _can_manage_config(current_user, tipo):
        raise AppError("Sem permissão para configurar integrações.", code="forbidden")
    data = ProvedorConfigCreate(
        tipo=IntegracaoTipo(tipo),
        provedor=provedor,
        nome=nome,
        filial_id=uuid.UUID(filial_id) if filial_id.strip() else None,
        client_id=client_id or None,
        client_secret=client_secret or None,
        api_key=api_key or None,
        base_url=base_url or None,
        webhook_secret=webhook_secret or None,
    )
    await ProvedorConfigService(session).create(current_user.tenant_id, data)
    slug = tipo if tipo != "transito" else "transito"
    return RedirectResponse(f"/integracoes/{slug}", status_code=303)


@router.post("/integracoes/configs/{config_id}/testar")
async def config_testar(
    request: Request,
    config_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_user)],
    tipo: Annotated[str, Form()] = "pagamentos",
):
    if not _can_manage_config(current_user, tipo, edit=True):
        raise AppError("Sem permissão para testar integrações.", code="forbidden")
    svc = ProvedorConfigService(session)
    ok = await svc.testar(config_id)
    config = await svc.get(config_id)
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse(
            content={
                "ok": ok,
                "status": config.status.value,
                "message": "Conexão verificada com sucesso." if ok else (config.ultimo_erro or "Falha no teste de conexão."),
            }
        )
    slug = tipo if tipo != "transito" else "transito"
    status = "ok" if ok else "fail"
    return RedirectResponse(
        f"/integracoes/{slug}?test={status}&config={config.nome}",
        status_code=303,
    )


@router.post("/integracoes/transito/multas")
async def transito_multas(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.transito.consultar"))
    ],
    veiculo_id: Annotated[str, Form()],
):
    await TransitoService(session).consultar_multas(
        current_user.tenant_id,
        TransitoMultasInput(veiculo_id=uuid.UUID(veiculo_id), importar=True),
    )
    return RedirectResponse("/integracoes/transito", status_code=303)


@router.post("/integracoes/transito/cnh")
async def transito_cnh(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.transito.consultar"))
    ],
    motorista_id: Annotated[str, Form()],
):
    await TransitoService(session).consultar_cnh(
        current_user.tenant_id,
        TransitoCnhInput(motorista_id=uuid.UUID(motorista_id), atualizar_pontuacao=True),
    )
    return RedirectResponse("/integracoes/transito", status_code=303)


@router.post("/integracoes/transito/debitos")
async def transito_debitos(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.transito.consultar"))
    ],
    veiculo_id: Annotated[str, Form()],
):
    await TransitoService(session).consultar_debitos(
        current_user.tenant_id,
        TransitoDebitosInput(veiculo_id=uuid.UUID(veiculo_id)),
    )
    return RedirectResponse("/integracoes/transito", status_code=303)


@router.post("/integracoes/credito/consultar")
async def credito_consultar(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.credito.consultar"))
    ],
    cliente_id: Annotated[str, Form()],
):
    await CreditoService(session).consultar(
        current_user.tenant_id,
        CreditoConsultaInput(cliente_id=uuid.UUID(cliente_id)),
    )
    return RedirectResponse("/integracoes/credito", status_code=303)


@router.post("/integracoes/telemetria/sincronizar")
async def telemetria_sync(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.telemetria.sincronizar"))
    ],
):
    await TelemetriaIntegracaoService(session).sincronizar(current_user.tenant_id)
    return RedirectResponse("/integracoes/telemetria", status_code=303)


@router.post("/integracoes/api/keys/novo", response_class=HTMLResponse)
async def api_key_novo(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.criar"))
    ],
    nome: Annotated[str, Form()],
    scopes: Annotated[list[str] | None, Form()] = None,
    scopes_csv: Annotated[str, Form()] = "",
) -> Any:
    scope_list = [s.strip() for s in (scopes or []) if s and s.strip()]
    if not scope_list and scopes_csv.strip():
        scope_list = [s.strip() for s in scopes_csv.split(",") if s.strip()]
    if not scope_list:
        scope_list = ["disponibilidade:read", "reservas:write", "contratos:read"]
    item, raw = await ApiKeyService(session).create(
        current_user.tenant_id,
        ApiKeyCreate(nome=nome, scopes=scope_list),
        user_id=current_user.id,
    )
    return render(
        request,
        "integracoes/api_key_created.html",
        {"title": "API Key criada", "key": item, "raw_key": raw},
    )


@router.get("/integracoes/api/keys/{key_id}/excluir", response_class=HTMLResponse)
async def api_key_excluir_confirmar(
    request: Request,
    key_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.editar"))
    ],
) -> Any:
    svc = ApiKeyService(session)
    key = await svc.get_for_tenant(current_user.tenant_id, key_id)
    return render(
        request,
        "integracoes/api_key_excluir.html",
        {
            "title": "Excluir API Key",
            "key": key,
            "scopes": sorted(svc.scopes(key)),
        },
    )


@router.post("/integracoes/api/keys/{key_id}/excluir", response_class=HTMLResponse)
async def api_key_excluir(
    request: Request,
    key_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.editar"))
    ],
) -> RedirectResponse:
    try:
        await ApiKeyService(session).delete(current_user.tenant_id, key_id)
        await session.commit()
        request.session["_flash"] = {
            "type": "success",
            "message": "API Key excluída. Integrações que usavam esta chave deixarão de funcionar.",
        }
    except AppError as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "error", "message": exc.message}
    return RedirectResponse("/integracoes/api", status_code=303)


@router.post("/integracoes/api/webhooks/novo")
async def outbound_webhook_novo(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.criar"))
    ],
    nome: Annotated[str, Form()],
    url: Annotated[str, Form()],
    secret: Annotated[str, Form()] = "",
    eventos: Annotated[list[str] | None, Form()] = None,
) -> RedirectResponse:
    await OutboundWebhookService(session).create(
        current_user.tenant_id,
        nome=nome,
        url=url,
        eventos=eventos or [],
        secret=secret or None,
    )
    return RedirectResponse("/integracoes/api", status_code=303)


@router.post("/integracoes/api/atendimento-webhook/regenerar")
async def atendimento_webhook_regenerar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.criar"))
    ],
) -> RedirectResponse:
    await SiteAtendimentoService(session).regenerate_token(current_user.tenant_id)
    await session.commit()
    request.session["_flash"] = {
        "type": "success",
        "message": "Token do webhook de atendimento regenerado. Atualize SITE_ATENDIMENTO_WEBHOOK_URL no Easypanel (serviço site).",
    }
    return RedirectResponse("/integracoes/api", status_code=303)


@router.post("/integracoes/api/webhooks/{webhook_id}/excluir")
async def outbound_webhook_excluir(
    webhook_id: uuid.UUID,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.criar"))
    ],
) -> RedirectResponse:
    try:
        await OutboundWebhookService(session).delete(webhook_id)
    except AppError:
        await session.rollback()
    return RedirectResponse("/integracoes/api", status_code=303)


@router.get("/integracoes/site/cores", response_class=HTMLResponse)
async def site_cores_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.site.visualizar"))
    ],
) -> HTMLResponse:
    tenant = await TenantService(session).get_tenant(current_user.tenant_id)
    can_edit = has_permission(
        current_user.permissions, "integracoes.site.editar", is_superuser=current_user.is_superuser
    )
    colors = resolved_site_colors(tenant)
    transition = site_transition_payload(tenant)
    return render(
        request,
        "integracoes/site_cores.html",
        {
            "title": "Website — Tema e cores",
            "tenant": tenant,
            "colors": colors,
            "tema": site_theme_payload(tenant),
            "transition": transition,
            "has_transition_image": tenant_has_transition_image(tenant),
            "can_edit": can_edit,
        },
    )


@router.post("/integracoes/site/cores", response_class=HTMLResponse)
async def site_cores_salvar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.site.editar"))
    ],
    transition_image: UploadFile | None = File(None),
) -> HTMLResponse:
    svc = TenantService(session)
    form = await request.form()
    try:
        size_raw = (form.get("site_transition_image_size_px") or "").strip()
        size_px = int(size_raw) if size_raw.isdigit() else None
        data = SiteThemeUpdate(
            site_primary_color=(form.get("site_primary_color") or "").strip() or None,
            site_background_color=(form.get("site_background_color") or "").strip() or None,
            site_text_color=(form.get("site_text_color") or "").strip() or None,
            site_header_bg_color=(form.get("site_header_bg_color") or "").strip() or None,
            site_header_text_color=(form.get("site_header_text_color") or "").strip() or None,
            site_topbar_bg_color=(form.get("site_topbar_bg_color") or "").strip() or None,
            site_topbar_tab_bg_color=(form.get("site_topbar_tab_bg_color") or "").strip() or None,
            site_topbar_tab_text_color=(form.get("site_topbar_tab_text_color") or "").strip() or None,
            site_topbar_tab_active_bg_color=(form.get("site_topbar_tab_active_bg_color") or "").strip() or None,
            site_topbar_tab_active_text_color=(form.get("site_topbar_tab_active_text_color") or "").strip() or None,
            site_button_bg_color=(form.get("site_button_bg_color") or "").strip() or None,
            site_button_text_color=(form.get("site_button_text_color") or "").strip() or None,
            site_link_color=(form.get("site_link_color") or "").strip() or None,
            site_border_color=(form.get("site_border_color") or "").strip() or None,
            site_surface_color=(form.get("site_surface_color") or "").strip() or None,
            site_text_muted_color=(form.get("site_text_muted_color") or "").strip() or None,
            site_footer_bg_color=(form.get("site_footer_bg_color") or "").strip() or None,
            site_footer_text_color=(form.get("site_footer_text_color") or "").strip() or None,
            site_transition_enabled=form.get("site_transition_enabled") == "on",
            site_transition_bg_color=(form.get("site_transition_bg_color") or "").strip() or None,
            site_transition_image_size_px=size_px,
            remove_transition_image=form.get("remove_transition_image") == "on",
            reset_defaults=form.get("reset_defaults") == "on",
        )
        await svc.update_site_theme(current_user.tenant_id, data)
        if transition_image and transition_image.filename:
            image_bytes = await transition_image.read()
            if image_bytes:
                await svc.upload_site_transition_image(
                    current_user.tenant_id,
                    image_bytes,
                    transition_image.filename,
                    transition_image.content_type or "image/png",
                )
        await session.commit()
        request.session["_flash"] = {
            "type": "success",
            "message": "Cores do site salvas. A alteração aparece no site em instantes.",
        }
        return RedirectResponse("/integracoes/site/cores", status_code=303)
    except (AppError, ValidationError) as exc:
        await session.rollback()
        tenant = await svc.get_tenant(current_user.tenant_id)
        colors = resolved_site_colors(tenant)
        transition = site_transition_payload(tenant)
        message = exc.message if isinstance(exc, AppError) else str(exc.errors()[0].get("msg", exc))
        return render(
            request,
            "integracoes/site_cores.html",
            {
                "title": "Website — Tema e cores",
                "tenant": tenant,
                "colors": colors,
                "tema": site_theme_payload(tenant),
                "transition": transition,
                "has_transition_image": tenant_has_transition_image(tenant),
                "can_edit": True,
                "error": message,
            },
            status_code=400,
        )


@router.get("/integracoes/site/slides", response_class=HTMLResponse)
async def site_slides_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.site.visualizar"))
    ],
) -> HTMLResponse:
    svc = SiteSlideService(session)
    slides = await svc.list_slides(current_user.tenant_id)
    can_edit = has_permission(
        current_user.permissions, "integracoes.site.editar", is_superuser=current_user.is_superuser
    )
    api_base = str(request.base_url).rstrip("/")
    items = [
        {
            "slide": slide,
            "preview_url": resolve_slide_image_url(slide, request_base=api_base),
        }
        for slide in slides
    ]
    return render(
        request,
        "integracoes/site_slides.html",
        {
            "title": "Website — Slides",
            "slides": items,
            "can_edit": can_edit,
            "max_slides": 10,
        },
    )


@router.post("/integracoes/site/slides/novo", response_class=HTMLResponse)
async def site_slides_novo(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.site.editar"))
    ],
    imagem: UploadFile = File(...),
    titulo: Annotated[str, Form()] = "",
    link_url: Annotated[str, Form()] = "",
) -> HTMLResponse:
    svc = SiteSlideService(session)
    try:
        file_bytes = await imagem.read()
        await svc.create_slide(
            current_user.tenant_id,
            file_bytes=file_bytes,
            filename=imagem.filename or "slide.jpg",
            content_type=imagem.content_type or "image/jpeg",
            titulo=titulo,
            link_url=link_url,
        )
        await session.commit()
        request.session["_flash"] = {"type": "success", "message": "Slide adicionado. Já está visível no site."}
        return RedirectResponse("/integracoes/site/slides", status_code=303)
    except AppError as exc:
        await session.rollback()
        slides = await svc.list_slides(current_user.tenant_id)
        api_base = str(request.base_url).rstrip("/")
        items = [
            {"slide": s, "preview_url": resolve_slide_image_url(s, request_base=api_base)}
            for s in slides
        ]
        return render(
            request,
            "integracoes/site_slides.html",
            {
                "title": "Website — Slides",
                "slides": items,
                "can_edit": True,
                "max_slides": 10,
                "error": exc.message,
            },
            status_code=400,
        )


@router.post("/integracoes/site/slides/{slide_id}/salvar", response_class=HTMLResponse)
async def site_slides_salvar(
    request: Request,
    slide_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.site.editar"))
    ],
    titulo: Annotated[str, Form()] = "",
    link_url: Annotated[str, Form()] = "",
    sort_order: Annotated[int, Form()] = 0,
    ativo: Annotated[str, Form()] = "",
) -> HTMLResponse:
    svc = SiteSlideService(session)
    try:
        await svc.update_slide(
            current_user.tenant_id,
            slide_id,
            titulo=titulo,
            link_url=link_url,
            sort_order=sort_order,
            ativo=ativo == "on" or ativo == "true" or ativo == "1",
        )
        await session.commit()
        request.session["_flash"] = {"type": "success", "message": "Slide atualizado."}
    except AppError as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "error", "message": exc.message}
    return RedirectResponse("/integracoes/site/slides", status_code=303)


@router.post("/integracoes/site/slides/{slide_id}/substituir-imagem", response_class=HTMLResponse)
async def site_slides_substituir_imagem(
    request: Request,
    slide_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.site.editar"))
    ],
    imagem: UploadFile = File(...),
) -> HTMLResponse:
    svc = SiteSlideService(session)
    try:
        file_bytes = await imagem.read()
        await svc.replace_image(
            current_user.tenant_id,
            slide_id,
            file_bytes=file_bytes,
            filename=imagem.filename or "slide.jpg",
            content_type=imagem.content_type or "image/jpeg",
        )
        await session.commit()
        request.session["_flash"] = {"type": "success", "message": "Imagem do slide substituída."}
    except AppError as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "error", "message": exc.message}
    return RedirectResponse("/integracoes/site/slides", status_code=303)


@router.post("/integracoes/site/slides/{slide_id}/excluir")
async def site_slides_excluir(
    request: Request,
    slide_id: uuid.UUID,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.site.editar"))
    ],
) -> RedirectResponse:
    svc = SiteSlideService(session)
    try:
        await svc.delete_slide(current_user.tenant_id, slide_id)
        await session.commit()
        request.session["_flash"] = {"type": "success", "message": "Slide removido do site."}
    except AppError as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "error", "message": exc.message}
    return RedirectResponse("/integracoes/site/slides", status_code=303)
