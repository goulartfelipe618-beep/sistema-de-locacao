"""Construtores de contexto para templates PDF por entidade."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.cadastros.models import Cliente
from app.modules.comercial.models import CrmProposta, CrmPropostaItem
from app.modules.comercial.service import PropostaService
from app.modules.financeiro.models import FinContaReceber
from app.modules.financeiro.service import ContaReceberService
from app.modules.fiscal.service import NfeService, NfseService
from app.modules.frota.models import FrotaCategoria, FrotaMarca, FrotaModelo, FrotaVeiculo
from app.modules.frota.service import VeiculoService
from app.modules.locacoes.models import LocAvaria, LocContrato, LocVistoria
from app.modules.locacoes.service import AvariaService, ContratoService
from app.modules.manutencao.models import ManOsItem
from app.modules.manutencao.service import OrdemServicoService
from app.modules.reservas.models import ResReserva, ResReservaItem
from app.modules.reservas.service import CotacaoService, ReservaService
from app.modules.tenants.models import Filial
from app.modules.tenants.repository import TenantRepository
from app.shared.enums import VistoriaTipo


async def _empresa(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    tenant = await TenantRepository(session).get(tenant_id)
    if tenant is None:
        raise NotFoundError("Empresa não encontrada.")
    return {
        "empresa_nome": tenant.trade_name or tenant.legal_name,
        "empresa_razao": tenant.legal_name,
        "empresa_cnpj": tenant.cnpj or "—",
        "empresa_email": tenant.email or "—",
        "empresa_phone": tenant.phone or "—",
    }


async def _filial_nome(session: AsyncSession, filial_id: uuid.UUID | None) -> str:
    if filial_id is None:
        return "—"
    row = await session.get(Filial, filial_id)
    return row.name if row else "—"


async def _cliente_nome(session: AsyncSession, cliente_id: uuid.UUID) -> str:
    row = await session.get(Cliente, cliente_id)
    return row.nome if row else str(cliente_id)


async def _veiculo_label(session: AsyncSession, veiculo_id: uuid.UUID | None) -> str:
    if veiculo_id is None:
        return "—"
    v = await session.get(FrotaVeiculo, veiculo_id)
    if v is None:
        return str(veiculo_id)
    modelo = await session.get(FrotaModelo, v.modelo_id)
    marca = await session.get(FrotaMarca, v.marca_id) if v.marca_id else None
    nome = f"{marca.nome if marca else ''} {modelo.nome if modelo else ''}".strip()
    return f"{v.placa} — {nome or 'Veículo'}"


async def build_reserva(session: AsyncSession, tenant_id: uuid.UUID, reserva_id: uuid.UUID) -> dict:
    reserva = await ReservaService(session).get(reserva_id)
    itens = (
        await session.execute(
            select(ResReservaItem).where(
                ResReservaItem.reserva_id == reserva_id,
                ResReservaItem.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Reserva {reserva.numero}",
            "reserva": reserva,
            "cliente_nome": await _cliente_nome(session, reserva.cliente_id),
            "veiculo_label": await _veiculo_label(session, reserva.veiculo_id),
            "filial_retirada": await _filial_nome(session, reserva.filial_retirada_id),
            "filial_devolucao": await _filial_nome(session, reserva.filial_devolucao_id),
            "itens": itens,
            "watermark": None,
        }
    )
    if reserva.status.value in ("cancelada", "no_show"):
        ctx["watermark"] = "CANCELADO"
    return ctx


async def build_cotacao(session: AsyncSession, tenant_id: uuid.UUID, cotacao_id: uuid.UUID) -> dict:
    cotacao = await CotacaoService(session).get(cotacao_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Cotação {cotacao.numero}",
            "cotacao": cotacao,
            "cliente_nome": await _cliente_nome(session, cotacao.cliente_id)
            if cotacao.cliente_id
            else "—",
            "veiculo_label": await _veiculo_label(session, cotacao.veiculo_id),
            "filial_retirada": await _filial_nome(session, cotacao.filial_retirada_id),
            "watermark": "EXPIRADA" if cotacao.status.value == "expirada" else None,
        }
    )
    return ctx


async def build_contrato(session: AsyncSession, tenant_id: uuid.UUID, contrato_id: uuid.UUID) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    ctx = await _empresa(session, tenant_id)
    watermark = None
    if contrato.status.value == "cancelado":
        watermark = "CANCELADO"
    elif contrato.status.value == "rascunho":
        watermark = "RASCUNHO"
    ctx.update(
        {
            "doc_titulo": f"Contrato {contrato.numero}",
            "contrato": contrato,
            "cliente_nome": await _cliente_nome(session, contrato.cliente_id),
            "veiculo_label": await _veiculo_label(session, contrato.veiculo_id),
            "filial_retirada": await _filial_nome(session, contrato.filial_retirada_id),
            "filial_devolucao": await _filial_nome(session, contrato.filial_devolucao_id),
            "watermark": watermark,
            "assinatura_b64": None,
        }
    )
    return ctx


async def build_vistoria(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    contrato_id: uuid.UUID,
    tipo: VistoriaTipo,
) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    vistoria = (
        await session.execute(
            select(LocVistoria)
            .where(
                LocVistoria.contrato_id == contrato_id,
                LocVistoria.tipo == tipo,
                LocVistoria.deleted_at.is_(None),
            )
            .order_by(LocVistoria.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    ctx = await build_contrato(session, tenant_id, contrato_id)
    ctx["doc_titulo"] = (
        "Termo de Vistoria (Check-out)"
        if tipo == VistoriaTipo.CHECKOUT
        else "Termo de Devolução (Check-in)"
    )
    ctx["vistoria"] = vistoria
    ctx["vistoria_tipo"] = tipo.value
    return ctx


async def build_avaria(session: AsyncSession, tenant_id: uuid.UUID, avaria_id: uuid.UUID) -> dict:
    avaria = await AvariaService(session).get(avaria_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Laudo de Avaria — {avaria.localizacao}",
            "avaria": avaria,
            "contrato_numero": None,
            "veiculo_label": await _veiculo_label(session, avaria.veiculo_id),
            "watermark": None,
        }
    )
    if avaria.contrato_id:
        c = await session.get(LocContrato, avaria.contrato_id)
        ctx["contrato_numero"] = c.numero if c else None
    return ctx


async def build_ordem_servico(
    session: AsyncSession, tenant_id: uuid.UUID, os_id: uuid.UUID
) -> dict:
    os = await OrdemServicoService(session).get(os_id)
    itens = (
        await session.execute(
            select(ManOsItem).where(
                ManOsItem.os_id == os_id,
                ManOsItem.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    ctx = await _empresa(session, tenant_id)
    watermark = "CANCELADA" if os.status.value == "cancelada" else None
    ctx.update(
        {
            "doc_titulo": f"OS {os.numero}",
            "os": os,
            "itens": itens,
            "veiculo_label": await _veiculo_label(session, os.veiculo_id),
            "filial_nome": await _filial_nome(session, os.filial_id),
            "watermark": watermark,
        }
    )
    return ctx


async def build_ficha_veiculo(
    session: AsyncSession, tenant_id: uuid.UUID, veiculo_id: uuid.UUID
) -> dict:
    veiculo = await VeiculoService(session).get(veiculo_id)
    modelo = await session.get(FrotaModelo, veiculo.modelo_id)
    marca = await session.get(FrotaMarca, veiculo.marca_id) if veiculo.marca_id else None
    categoria = await session.get(FrotaCategoria, veiculo.categoria_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Ficha — {veiculo.placa}",
            "veiculo": veiculo,
            "marca_nome": marca.nome if marca else "—",
            "modelo_nome": modelo.nome if modelo else "—",
            "categoria_nome": categoria.nome if categoria else "—",
            "filial_nome": await _filial_nome(session, veiculo.filial_id),
            "watermark": "BAIXADO" if veiculo.status.value == "baixado" else None,
        }
    )
    return ctx


async def build_proposta(
    session: AsyncSession, tenant_id: uuid.UUID, proposta_id: uuid.UUID
) -> dict:
    proposta = await PropostaService(session).get(proposta_id)
    itens = (
        await session.execute(
            select(CrmPropostaItem).where(
                CrmPropostaItem.proposta_id == proposta_id,
                CrmPropostaItem.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    ctx = await _empresa(session, tenant_id)
    watermark = None
    if proposta.status.value in ("recusada", "expirada"):
        watermark = proposta.status.value.upper()
    ctx.update(
        {
            "doc_titulo": f"Proposta {proposta.numero}",
            "proposta": proposta,
            "itens": itens,
            "cliente_nome": await _cliente_nome(session, proposta.cliente_id)
            if proposta.cliente_id
            else "—",
            "watermark": watermark,
        }
    )
    return ctx


async def build_recibo_pagamento(
    session: AsyncSession, tenant_id: uuid.UUID, titulo_id: uuid.UUID
) -> dict:
    titulo = await ContaReceberService(session).get(titulo_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Recibo {titulo.numero}",
            "titulo": titulo,
            "cliente_nome": await _cliente_nome(session, titulo.cliente_id)
            if titulo.cliente_id
            else "—",
            "filial_nome": await _filial_nome(session, titulo.filial_id),
            "watermark": None,
        }
    )
    return ctx


async def build_danfe(
    session: AsyncSession, tenant_id: uuid.UUID, nfe_id: uuid.UUID
) -> dict:
    nfe_svc = NfeService(session)
    nfe = await nfe_svc.get(nfe_id)
    itens = await nfe_svc.list_nfe_itens(nfe_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"DANFE {nfe.numero}",
            "nfe": nfe,
            "itens": itens,
            "filial_nome": await _filial_nome(session, nfe.filial_id),
            "watermark": None,
        }
    )
    return ctx


async def build_danfse(
    session: AsyncSession, tenant_id: uuid.UUID, nfse_id: uuid.UUID
) -> dict:
    nfse = await NfseService(session).get(nfse_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"DANFSE {nfse.numero}",
            "nfse": nfse,
            "filial_nome": await _filial_nome(session, nfse.filial_id),
            "cliente_nome": await _cliente_nome(session, nfse.cliente_id)
            if nfse.cliente_id
            else "Consumidor não identificado",
            "watermark": None,
        }
    )
    return ctx


async def build_relatorio_analitico(
    titulo: str,
    columns: list[str],
    rows: list[list[Any]],
    summary: dict[str, Any],
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> dict:
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": titulo,
            "columns": columns,
            "rows": rows,
            "summary": summary,
            "watermark": None,
        }
    )
    return ctx


BUILDERS: dict[str, str] = {
    "reserva_confirmacao": "reserva",
    "reserva_voucher": "reserva",
    "cotacao": "cotacao",
    "contrato_locacao": "contrato",
    "vistoria_checkout": "contrato",
    "vistoria_checkin": "contrato",
    "laudo_avaria": "avaria",
    "ordem_servico": "ordem_servico",
    "ficha_veiculo": "veiculo",
    "proposta_comercial": "proposta",
    "recibo_pagamento": "conta_receber",
}


async def build_context(
    session: AsyncSession,
    template_id: str,
    tenant_id: uuid.UUID,
    entidade_id: uuid.UUID,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Despacha construção de contexto conforme template."""
    extra = extra or {}
    if template_id in ("reserva_confirmacao", "reserva_voucher"):
        ctx = await build_reserva(session, tenant_id, entidade_id)
        ctx["doc_titulo"] = (
            "Confirmação de Reserva" if template_id == "reserva_confirmacao" else "Voucher de Reserva"
        )
        return ctx
    if template_id == "cotacao":
        return await build_cotacao(session, tenant_id, entidade_id)
    if template_id == "contrato_locacao":
        return await build_contrato(session, tenant_id, entidade_id)
    if template_id == "vistoria_checkout":
        return await build_vistoria(session, tenant_id, entidade_id, VistoriaTipo.CHECKOUT)
    if template_id == "vistoria_checkin":
        return await build_vistoria(session, tenant_id, entidade_id, VistoriaTipo.CHECKIN)
    if template_id == "laudo_avaria":
        return await build_avaria(session, tenant_id, entidade_id)
    if template_id == "ordem_servico":
        return await build_ordem_servico(session, tenant_id, entidade_id)
    if template_id == "ficha_veiculo":
        return await build_ficha_veiculo(session, tenant_id, entidade_id)
    if template_id == "proposta_comercial":
        return await build_proposta(session, tenant_id, entidade_id)
    if template_id == "recibo_pagamento":
        return await build_recibo_pagamento(session, tenant_id, entidade_id)
    if template_id == "danfe":
        return await build_danfe(session, tenant_id, entidade_id)
    if template_id == "danfse":
        return await build_danfse(session, tenant_id, entidade_id)
    if template_id == "relatorio_analitico":
        return await build_relatorio_analitico(
            extra.get("titulo", "Relatório"),
            extra.get("columns", []),
            extra.get("rows", []),
            extra.get("summary", {}),
            tenant_id,
            session,
        )
    raise NotFoundError(f"Template desconhecido: {template_id}")
