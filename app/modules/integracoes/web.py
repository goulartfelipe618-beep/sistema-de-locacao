"""Rotas Web do módulo Integrações (§12)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
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
from app.modules.integracoes.service import (
    ApiKeyService,
    CreditoService,
    ProvedorConfigService,
    TelemetriaIntegracaoService,
    TransitoService,
    WebhookLogService,
)
from app.modules.tenants.service import FilialService
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
    ("disponibilidade:read", "Consultar disponibilidade"),
    ("veiculos:read", "Listar veículos publicados no site"),
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
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("integracoes.api_publica.visualizar"))
    ],
) -> Any:
    keys = await ApiKeyService(session).list_items(PageParams(page=1, size=50))
    webhooks = await OutboundWebhookService(session).list_items(PageParams(page=1, size=50))
    return render(
        request,
        "integracoes/api_publica.html",
        {
            "title": "API Pública",
            "keys": keys.items,
            "webhooks": webhooks.items,
            "outbound_eventos": OUTBOUND_EVENTOS,
            "api_scopes": API_PUBLIC_SCOPES,
            "docs_url": "/docs",
            "openapi_url": "/openapi.json",
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
