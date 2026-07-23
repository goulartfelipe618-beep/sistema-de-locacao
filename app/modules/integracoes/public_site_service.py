"""Serviços de catálogo e reserva para o site (fonte única: cadastros do ERP)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.cadastros.models import Cliente
from app.modules.cadastros.schemas import ClienteCreate
from app.modules.cadastros.service import ClienteService
from app.modules.frota.models import FrotaCategoria, FrotaModelo, FrotaVeiculo
from app.modules.frota.veiculo_fotos import public_veiculo_capa_url, veiculo_tem_foto_capa
from app.modules.frota.service import CategoriasService
from app.modules.integracoes.public_schemas import (
    PublicClienteInput,
    PublicCotacaoSiteCreate,
    PublicCotacaoSiteRead,
    PublicReservaSiteCreate,
)
from app.modules.intermediacao.service import IntermediacaoService
from app.modules.reservas.schemas import ReservaCreate
from app.modules.reservas.service import DisponibilidadeService, ReservaService
from app.modules.tenants.branding import resolve_logo_url
from app.modules.tenants.site_theme import site_theme_payload
from app.modules.tenants.models import Tenant
from app.modules.tenants.setup import format_tenant_address
from app.modules.tenants.service import FilialService
from app.shared.enums import CadastroStatus, FilialStatus, PersonType, ReservaOrigem, TarifarioCanal
from app.core.pagination import PageParams


def _format_cnpj(raw: str | None) -> str | None:
    if not raw or len(raw) != 14:
        return raw
    return f"{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}"


async def get_empresa_public(session: AsyncSession, tenant_id: uuid.UUID) -> dict:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError("Empresa não encontrada.")
    return {
        "slug": tenant.slug,
        "razao_social": tenant.legal_name,
        "nome_fantasia": tenant.trade_name or tenant.sidebar_display_name,
        "nome_exibicao": tenant.sidebar_display_name,
        "cnpj": tenant.cnpj,
        "cnpj_formatado": _format_cnpj(tenant.cnpj),
        "ie": tenant.ie,
        "email": tenant.email,
        "telefone": tenant.phone,
        "website": tenant.website,
        "logo_url": resolve_logo_url(tenant),
        "endereco_formatado": format_tenant_address(tenant),
        "cidade": tenant.city,
        "uf": tenant.state,
        "rodape_documentos": tenant.document_footer_text,
        "tema": site_theme_payload(tenant),
    }


async def list_filiais_public(session: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    page = await FilialService(session).list_filiais(PageParams(page=1, size=200))
    items = []
    for f in page.items:
        if f.status != FilialStatus.ACTIVE:
            continue
        if f.tenant_id != tenant_id:
            continue
        items.append(
            {
                "id": str(f.id),
                "codigo": f.code,
                "nome": f.name,
                "cidade": f.city,
                "uf": f.state,
            }
        )
    return items


async def list_grupos_public(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    filial_id: uuid.UUID | None = None,
    retirada_em: datetime | None = None,
    devolucao_em: datetime | None = None,
) -> list[dict]:
    """Grupos (categorias) ativos com veículos elegíveis ao site."""
    cats = await CategoriasService(session).list_items(PageParams(page=1, size=500))
    disp_map: dict[uuid.UUID, int] = {}
    if filial_id and retirada_em and devolucao_em:
        disp = await DisponibilidadeService(session).consultar(
            filial_id, retirada_em, devolucao_em
        )
        disp_map = {r.categoria_id: r.livres for r in disp}

    svc = IntermediacaoService(session)
    veiculos = await svc.list_veiculos_site(tenant_id, filial_id=filial_id)
    capa_por_categoria: dict[uuid.UUID, str] = {}
    count_por_cat: dict[uuid.UUID, int] = {}
    for item in veiculos:
        cid = uuid.UUID(item["categoria_id"])
        veiculo = await session.get(FrotaVeiculo, uuid.UUID(item["id"]))
        if veiculo is None:
            continue
        if retirada_em and devolucao_em:
            ok, _ = await svc.veiculo_disponivel_periodo(veiculo, retirada_em, devolucao_em)
            if not ok:
                continue
        count_por_cat[cid] = count_por_cat.get(cid, 0) + 1
        if veiculo_tem_foto_capa(veiculo) and cid not in capa_por_categoria:
            capa_por_categoria[cid] = public_veiculo_capa_url(veiculo.id)

    out: list[dict] = []
    for cat in cats.items:
        if cat.status != CadastroStatus.ACTIVE:
            continue
        qtd = count_por_cat.get(cat.id, 0)
        if retirada_em and devolucao_em and qtd == 0:
            continue
        if not retirada_em and qtd == 0:
            continue
        livres = disp_map.get(cat.id, qtd) if disp_map else qtd
        imagem_url = capa_por_categoria.get(cat.id) or cat.imagem_url
        out.append(
            {
                "id": str(cat.id),
                "nome": cat.nome,
                "descricao": cat.descricao,
                "imagem_url": imagem_url,
                "capacidade_passageiros": cat.capacidade_passageiros,
                "capacidade_porta_malas": cat.capacidade_porta_malas,
                "transmissao_tipica": cat.transmissao_tipica,
                "grupo_tarifario": cat.grupo_tarifario,
                "ordem": cat.ordem,
                "veiculos_disponiveis": livres,
            }
        )
    out.sort(key=lambda x: (x["ordem"], x["nome"]))
    return out


async def list_veiculos_public(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    filial_id: uuid.UUID | None = None,
    categoria_id: uuid.UUID | None = None,
    retirada_em: datetime | None = None,
    devolucao_em: datetime | None = None,
) -> list[dict]:
    """Veículos publicáveis — sem placa/chassi (site)."""
    svc = IntermediacaoService(session)
    rows = await svc.list_veiculos_site(
        tenant_id, filial_id=filial_id, categoria_id=categoria_id
    )
    cat_names: dict[uuid.UUID, str] = {}
    modelo_cache: dict[uuid.UUID, str] = {}

    async def modelo_label(veiculo: FrotaVeiculo) -> str | None:
        if not veiculo.modelo_id:
            return None
        if veiculo.modelo_id in modelo_cache:
            return modelo_cache[veiculo.modelo_id]
        m = await session.get(FrotaModelo, veiculo.modelo_id)
        nome = m.nome if m else None
        if nome:
            modelo_cache[veiculo.modelo_id] = nome
        return nome

    result: list[dict] = []
    for item in rows:
        veiculo = await session.get(FrotaVeiculo, uuid.UUID(item["id"]))
        if veiculo is None:
            continue
        if retirada_em and devolucao_em:
            ok, _ = await svc.veiculo_disponivel_periodo(veiculo, retirada_em, devolucao_em)
            if not ok:
                continue
        cid = veiculo.categoria_id
        if cid not in cat_names:
            c = await session.get(FrotaCategoria, cid)
            cat_names[cid] = c.nome if c else ""
        result.append(
            {
                "id": str(veiculo.id),
                "categoria_id": str(cid),
                "categoria_nome": cat_names[cid],
                "filial_id": str(veiculo.filial_id) if veiculo.filial_id else None,
                "modelo_nome": await modelo_label(veiculo),
                "ano_modelo": veiculo.ano_modelo,
                "cor": veiculo.cor,
                "imagem_url": public_veiculo_capa_url(veiculo.id)
                if veiculo_tem_foto_capa(veiculo)
                else None,
            }
        )
    return result


async def _resolve_cliente_site(
    session: AsyncSession, tenant_id: uuid.UUID, data: PublicClienteInput
) -> Cliente:
    svc = ClienteService(session)
    existing = await svc.repo.get_by_cpf(data.cpf)
    if existing:
        return existing
    return await svc.create(
        tenant_id,
        ClienteCreate(
            person_type=PersonType.NATURAL,
            nome=data.nome,
            cpf=data.cpf,
            email=str(data.email),
            telefone=data.telefone,
            celular=data.telefone,
        ),
    )


async def criar_reserva_site(
    session: AsyncSession, tenant_id: uuid.UUID, payload: PublicReservaSiteCreate
) -> dict:
    cliente = await _resolve_cliente_site(session, tenant_id, payload.cliente)
    devolucao_filial = payload.filial_devolucao_id or payload.filial_retirada_id
    if payload.devolucao_em <= payload.retirada_em:
        raise ValidationError("Devolução deve ser posterior à retirada.")
    data = ReservaCreate(
        cliente_id=cliente.id,
        categoria_id=payload.categoria_id,
        filial_retirada_id=payload.filial_retirada_id,
        filial_devolucao_id=devolucao_filial,
        retirada_em=payload.retirada_em,
        devolucao_em=payload.devolucao_em,
        origem=ReservaOrigem.WEBSITE,
        veiculo_id=payload.veiculo_id,
        cupom_codigo=payload.cupom_codigo,
        protecao_ids=payload.protecao_ids,
        taxa_ids=payload.taxa_ids,
        observacoes=payload.observacoes,
    )
    reserva = await ReservaService(session).create(tenant_id, data)
    return {
        "id": str(reserva.id),
        "numero": reserva.numero,
        "status": reserva.status.value,
        "valor_total": str(reserva.valor_total),
        "cliente_id": str(cliente.id),
    }


async def cotacao_site(
    session: AsyncSession, tenant_id: uuid.UUID, payload: PublicCotacaoSiteCreate
) -> PublicCotacaoSiteRead:
    from app.modules.comercial.schemas import CupomValidarInput
    from app.modules.comercial.service import CupomService
    from app.modules.tarifario.schemas import PricingQuoteInput
    from app.modules.tarifario.service import PricingService

    devolucao_filial = payload.filial_devolucao_id or payload.filial_retirada_id
    one_way = devolucao_filial != payload.filial_retirada_id
    quote_input = PricingQuoteInput(
        tenant_id=tenant_id,
        filial_id=payload.filial_retirada_id,
        categoria_id=payload.categoria_id,
        canal=TarifarioCanal.SITE,
        retirada_em=payload.retirada_em,
        devolucao_em=payload.devolucao_em,
        veiculo_id=payload.veiculo_id,
        protecao_ids=payload.protecao_ids,
        taxa_ids=payload.taxa_ids,
        one_way=one_way,
    )
    quote = await PricingService(session).calcular(quote_input)
    desconto = Decimal("0")
    if payload.cupom_codigo:
        cupom = await CupomService(session).validar(
            CupomValidarInput(
                codigo=payload.cupom_codigo,
                cliente_id=None,
                categoria_id=payload.categoria_id,
                valor_base=quote.total,
            )
        )
        if cupom.ok and cupom.desconto:
            desconto = cupom.desconto
    total_final = max(Decimal("0"), quote.total - desconto)
    return PublicCotacaoSiteRead(
        diaria_unitaria=quote.diaria_unitaria,
        dias=quote.dias,
        dias_cobrados=quote.dias_cobrados,
        subtotal_diarias=quote.subtotal_diarias,
        subtotal_taxas=quote.subtotal_taxas,
        subtotal_protecoes=quote.subtotal_protecoes,
        total=quote.total,
        tabela_nome=quote.tabela_nome,
        km_livre=quote.km_livre,
        desconto_cupom=desconto,
        total_com_desconto=total_final,
    )


async def list_slides_public(session: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    """Slides ativos do carrossel do site."""
    from app.modules.integracoes.site_slides import SiteSlideService

    slides = await SiteSlideService(session).list_slides(tenant_id, active_only=True)
    return [
        {
            "id": str(slide.id),
            "titulo": slide.titulo,
            "ordem": slide.sort_order,
            "link_url": slide.link_url,
            "imagem_url": f"/api/v1/public/slides/{slide.id}/imagem",
        }
        for slide in slides
    ]
