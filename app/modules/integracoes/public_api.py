"""API pública autenticada por API Key (§12.5) — site B2C consome somente estes endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.requests import Request
from starlette.responses import Response

from app import __version__
from app.modules.integracoes.deps import PublicSessionDep, require_api_key_scope
from app.modules.integracoes.models import IntApiKey
from app.modules.integracoes.public_schemas import (
    PublicContatoSiteCreate,
    PublicCotacaoSiteCreate,
    PublicCotacaoSiteRead,
    PublicReservaSiteCreate,
)
from app.modules.integracoes.public_site_service import (
    cotacao_site,
    criar_reserva_site,
    get_empresa_public,
    list_filiais_public,
    list_grupos_public,
    list_slides_public,
    list_veiculos_public,
)
from app.modules.integracoes.site_atendimento import SiteAtendimentoService, build_atendimento_webhook_url
from app.modules.integracoes.outbound import notify_outbound_event
from app.modules.integracoes.site_slides import SiteSlideService, decode_slide_image_bytes
from app.modules.locacoes.service import ContratoService
from app.modules.reservas.schemas import ReservaCreate
from app.modules.reservas.service import DisponibilidadeService, ReservaService
from app.shared.enums import ReservaOrigem

public_router = APIRouter(prefix="/public", tags=["API Pública"])


@public_router.get("/ping")
async def public_ping(
    key: Annotated[IntApiKey, Depends(require_api_key_scope("catalogo:read"))],
) -> dict:
    """Health check para o site (indicador “API conectada”)."""
    return {"ok": True, "tenant_id": str(key.tenant_id), "api_version": __version__}


@public_router.get("/empresa")
async def public_empresa(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("catalogo:read"))],
) -> dict:
    """Dados cadastrais e branding (logo, CNPJ, endereço) — editados no ERP."""
    return await get_empresa_public(session, key.tenant_id)


@public_router.get("/filiais")
async def public_filiais(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("catalogo:read"))],
) -> list[dict]:
    """Lojas/pontos de retirada ativos."""
    return await list_filiais_public(session, key.tenant_id)


@public_router.get("/slides")
async def public_slides(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("catalogo:read"))],
) -> list[dict]:
    """Slides do carrossel hero do site (imagens via GET /slides/{id}/imagem)."""
    return await list_slides_public(session, key.tenant_id)


@public_router.get("/slides/{slide_id}/imagem")
async def public_slide_imagem(
    slide_id: uuid.UUID,
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("catalogo:read"))],
) -> Response:
    """Bytes da imagem do slide (proxy seguro para o site via BFF)."""
    slide = await SiteSlideService(session).get(key.tenant_id, slide_id)
    if not slide.ativo:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Slide não encontrado.")
    data, content_type = decode_slide_image_bytes(slide)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@public_router.get("/grupos")
async def public_grupos(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("catalogo:read"))],
    filial_id: uuid.UUID | None = Query(None),
    retirada_em: datetime | None = Query(None),
    devolucao_em: datetime | None = Query(None),
) -> list[dict]:
    """Grupos de veículos (categorias) com estoque elegível ao site no período."""
    return await list_grupos_public(
        session,
        key.tenant_id,
        filial_id=filial_id,
        retirada_em=retirada_em,
        devolucao_em=devolucao_em,
    )


@public_router.post("/cotacao", response_model=PublicCotacaoSiteRead)
async def public_cotacao(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("pricing:read"))],
    payload: PublicCotacaoSiteCreate,
) -> PublicCotacaoSiteRead:
    """Cotação com canal SITE (tarifário, taxas e proteções cadastrados no ERP)."""
    return await cotacao_site(session, key.tenant_id, payload)


@public_router.post("/reservas/site", status_code=201)
async def public_criar_reserva_site(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("reservas:write"))],
    payload: PublicReservaSiteCreate,
) -> dict:
    """Cria reserva + cliente (find-or-create) com origem website."""
    return await criar_reserva_site(session, key.tenant_id, payload)


@public_router.get("/disponibilidade")
async def public_disponibilidade(
    session: PublicSessionDep,
    _key: Annotated[IntApiKey, Depends(require_api_key_scope("disponibilidade:read"))],
    filial_id: uuid.UUID = Query(...),
    retirada_em: datetime = Query(...),
    devolucao_em: datetime = Query(...),
) -> list[dict]:
    result = await DisponibilidadeService(session).consultar(
        filial_id, retirada_em, devolucao_em
    )
    return [
        {
            "categoria_id": str(r.categoria_id),
            "nome": r.nome,
            "livres": r.livres,
            "ocupados": r.ocupados,
            "total_frota": r.total_frota,
        }
        for r in result
    ]


@public_router.post("/reservas", status_code=201)
async def public_criar_reserva(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("reservas:write"))],
    payload: ReservaCreate,
) -> dict:
    """Legado: exige cliente_id. Origem forçada para website."""
    data = payload.model_copy(update={"origem": ReservaOrigem.WEBSITE})
    reserva = await ReservaService(session).create(key.tenant_id, data)
    return {"id": str(reserva.id), "numero": reserva.numero, "status": reserva.status.value}


@public_router.get("/veiculos")
async def public_veiculos(
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("veiculos:read"))],
    filial_id: uuid.UUID | None = Query(None),
    categoria_id: uuid.UUID | None = Query(None),
    retirada_em: datetime | None = Query(None),
    devolucao_em: datetime | None = Query(None),
) -> list[dict]:
    """Veículos publicáveis (sem placa). Mesmas regras: publicar_site, disponível, modo operação."""
    return await list_veiculos_public(
        session,
        key.tenant_id,
        filial_id=filial_id,
        categoria_id=categoria_id,
        retirada_em=retirada_em,
        devolucao_em=devolucao_em,
    )


@public_router.get("/veiculos/{veiculo_id}/capa/imagem")
async def public_veiculo_capa_imagem(
    veiculo_id: uuid.UUID,
    session: PublicSessionDep,
    key: Annotated[IntApiKey, Depends(require_api_key_scope("veiculos:read"))],
) -> Response:
    """Foto de capa do veículo (destaque no site)."""
    from app.modules.frota.service import VeiculoService
    from app.modules.frota.veiculo_fotos import VeiculoCapaService

    veiculo = await VeiculoService(session).get(veiculo_id)
    if veiculo.tenant_id != key.tenant_id:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Veículo não encontrado.")
    data, content_type = await VeiculoCapaService(session).resolve_capa_bytes(veiculo)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@public_router.post("/webhooks/atendimento", status_code=201)
async def public_webhook_atendimento(
    payload: PublicContatoSiteCreate,
    token: str = Query(..., min_length=16),
) -> dict:
    """Recebe contato do formulário de atendimento do site (token em Integrações → API Pública)."""
    from app.core import context
    from app.core.database import UnitOfWork

    async with UnitOfWork(tenant_id=None) as uow:
        tenant_id = await SiteAtendimentoService(uow.session).resolve_tenant_id_by_token(token)

    async with UnitOfWork(tenant_id=tenant_id) as uow:
        context.set_tenant_id(tenant_id)
        raw = await SiteAtendimentoService(uow.session).registrar_contato(tenant_id, payload)
        await uow.commit()

    outbound = raw.pop("_outbound_payload", None)
    if outbound:
        await notify_outbound_event(tenant_id, "contato.site", outbound)
    return raw


@public_router.get("/contratos/{contrato_id}")
async def public_status_contrato(
    contrato_id: uuid.UUID,
    session: PublicSessionDep,
    _key: Annotated[IntApiKey, Depends(require_api_key_scope("contratos:read"))],
) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    return {
        "id": str(contrato.id),
        "numero": contrato.numero,
        "status": contrato.status.value,
        "cliente_id": str(contrato.cliente_id),
        "veiculo_id": str(contrato.veiculo_id),
    }
