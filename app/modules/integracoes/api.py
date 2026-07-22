"""API REST do módulo Integrações (§12)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import Response

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.identity.service import AuthenticatedUser
from app.modules.integracoes.schemas import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    ConsultaRead,
    CreditoConsultaInput,
    ProvedorConfigCreate,
    ProvedorConfigRead,
    ProvedorConfigUpdate,
    TransitoCnhInput,
    TransitoDebitosInput,
    TransitoMultasInput,
    WebhookEventoRead,
)
from app.modules.integracoes.service import (
    ApiKeyService,
    CreditoService,
    PagamentoWebhookService,
    ProvedorConfigService,
    TelemetriaIntegracaoService,
    TransitoService,
    WebhookLogService,
)
from app.shared.enums import IntegracaoTipo

router = APIRouter(prefix="/integracoes", tags=["Integrações"])


@router.get("/configs", response_model=dict)
async def list_configs(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.pagamentos.visualizar"))
    ],
    tipo: IntegracaoTipo | None = None,
    page: int = Query(1, ge=1),
) -> dict:
    result = await ProvedorConfigService(session).list_items(PageParams(page=page, size=50), tipo=tipo)
    return {
        "items": [ProvedorConfigRead.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    }


@router.post("/configs", response_model=ProvedorConfigRead, status_code=status.HTTP_201_CREATED)
async def create_config(
    session: ApiSessionDep,
    payload: ProvedorConfigCreate,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.pagamentos.criar"))
    ],
) -> ProvedorConfigRead:
    item = await ProvedorConfigService(session).create(current_user.tenant_id, payload)
    return ProvedorConfigRead.model_validate(item)


@router.patch("/configs/{config_id}", response_model=ProvedorConfigRead)
async def update_config(
    config_id: uuid.UUID,
    session: ApiSessionDep,
    payload: ProvedorConfigUpdate,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.pagamentos.editar"))
    ],
) -> ProvedorConfigRead:
    item = await ProvedorConfigService(session).update(config_id, payload)
    return ProvedorConfigRead.model_validate(item)


@router.post("/configs/{config_id}/testar")
async def testar_config(
    config_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.pagamentos.editar"))
    ],
) -> dict:
    ok = await ProvedorConfigService(session).testar(config_id)
    return {"ok": ok}


@router.post("/transito/multas", response_model=ConsultaRead)
async def consultar_multas(
    session: ApiSessionDep,
    payload: TransitoMultasInput,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.transito.consultar"))
    ],
) -> ConsultaRead:
    item = await TransitoService(session).consultar_multas(current_user.tenant_id, payload)
    return ConsultaRead.model_validate(item)


@router.post("/transito/cnh", response_model=ConsultaRead)
async def consultar_cnh(
    session: ApiSessionDep,
    payload: TransitoCnhInput,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.transito.consultar"))
    ],
) -> ConsultaRead:
    item = await TransitoService(session).consultar_cnh(current_user.tenant_id, payload)
    return ConsultaRead.model_validate(item)


@router.post("/transito/debitos", response_model=ConsultaRead)
async def consultar_debitos(
    session: ApiSessionDep,
    payload: TransitoDebitosInput,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.transito.consultar"))
    ],
) -> ConsultaRead:
    item = await TransitoService(session).consultar_debitos(current_user.tenant_id, payload)
    return ConsultaRead.model_validate(item)


@router.post("/credito/consultar", response_model=ConsultaRead)
async def consultar_credito(
    session: ApiSessionDep,
    payload: CreditoConsultaInput,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.credito.consultar"))
    ],
) -> ConsultaRead:
    item = await CreditoService(session).consultar(current_user.tenant_id, payload)
    return ConsultaRead.model_validate(item)


@router.post("/telemetria/sincronizar")
async def sincronizar_telemetria(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.telemetria.sincronizar"))
    ],
    config_id: uuid.UUID | None = None,
) -> dict:
    return await TelemetriaIntegracaoService(session).sincronizar(
        current_user.tenant_id, config_id=config_id
    )


@router.get("/webhooks", response_model=dict)
async def list_webhooks(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.pagamentos.visualizar"))
    ],
    page: int = Query(1, ge=1),
) -> dict:
    result = await WebhookLogService(session).list_items(PageParams(page=page, size=50))
    return {
        "items": [WebhookEventoRead.model_validate(i) for i in result.items],
        "total": result.total,
    }


@router.get("/api-keys", response_model=list[ApiKeyRead])
async def list_api_keys(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.api_publica.visualizar"))
    ],
) -> list[ApiKeyRead]:
    result = await ApiKeyService(session).list_items(PageParams(page=1, size=100))
    return [ApiKeyRead.model_validate(i) for i in result.items]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    session: ApiSessionDep,
    payload: ApiKeyCreate,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.api_publica.criar"))
    ],
) -> ApiKeyCreated:
    item, raw = await ApiKeyService(session).create(
        current_user.tenant_id, payload, user_id=current_user.id
    )
    data = ApiKeyCreated.model_validate(item)
    return data.model_copy(update={"raw_key": raw})


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    session: ApiSessionDep,
    user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("integracoes.api_publica.editar"))
    ],
) -> Response:
    await ApiKeyService(session).delete(user.tenant_id, key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhooks_router.post("/pagamentos/{provider}")
async def webhook_pagamentos(
    provider: str,
    request: Request,
    token: str = Query(..., description="Token público da configuração"),
    tenant: str = Query(..., description="Slug do tenant"),
) -> dict:
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")
    from app.core.database import UnitOfWork
    from app.modules.tenants.repository import TenantRepository

    async with UnitOfWork(tenant_id=None) as uow:
        tenant_row = await TenantRepository(uow.session).get_by_slug(tenant)
    if tenant_row is None:
        return {"ok": False, "error": "tenant not found"}
    async with UnitOfWork(tenant_id=tenant_row.id) as uow:
        cfg = await ProvedorConfigService(uow.session).get_by_webhook_token(token)
        if cfg is None:
            return {"ok": False, "error": "config not found"}
        evento = await PagamentoWebhookService(uow.session).processar(
            provider=provider,
            token=token,
            body=body,
            signature=signature,
        )
    return {"ok": True, "evento_id": str(evento.id), "status": evento.status.value}
