"""Contexto da tela Dossiê do veículo."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cadastros.models_extra import Fornecedor
from app.modules.frota.models import (
    FrotaCategoria,
    FrotaCombustivel,
    FrotaDocumento,
    FrotaMarca,
    FrotaModelo,
    FrotaTelemetriaDispositivo,
    FrotaVeiculo,
    FrotaVeiculoAcessorio,
    FrotaVeiculoFoto,
)
from app.modules.frota.service import VeiculoService
from app.modules.intermediacao.models import FornecedorContratoLocacao
from app.modules.locacoes.models import LocContrato
from app.modules.manutencao.models import ManOrdemServico
from app.modules.reservas.models import ResReserva
from app.modules.tenants.models import Filial
from app.shared.enums import OrdemServicoStatus, ReservaStatus


@dataclass
class VeiculoDossier:
    veiculo: FrotaVeiculo
    categoria_nome: str | None = None
    marca_nome: str | None = None
    modelo_nome: str | None = None
    combustivel_nome: str | None = None
    filial_nome: str | None = None
    fornecedor_nome: str | None = None
    contrato_fornecedor_numero: str | None = None
    stats: dict[str, int | Decimal] = field(default_factory=dict)
    documentos: list[FrotaDocumento] = field(default_factory=list)
    fotos: list[FrotaVeiculoFoto] = field(default_factory=list)
    acessorios_count: int = 0
    telemetria: FrotaTelemetriaDispositivo | None = None
    reservas_recentes: list[ResReserva] = field(default_factory=list)
    contratos_recentes: list[LocContrato] = field(default_factory=list)
    ordens_recentes: list[ManOrdemServico] = field(default_factory=list)


async def _label(session: AsyncSession, model: type, entity_id: uuid.UUID | None) -> str | None:
    if not entity_id:
        return None
    row = await session.get(model, entity_id)
    if row is None:
        return None
    return getattr(row, "nome", None) or getattr(row, "name", None)


async def build_veiculo_dossier(session: AsyncSession, veiculo_id: uuid.UUID) -> VeiculoDossier:
    veiculo = await VeiculoService(session).get(veiculo_id)
    vid = veiculo_id

    contrato_fornecedor_numero = None
    if veiculo.contrato_fornecedor_id:
        cf = await session.get(FornecedorContratoLocacao, veiculo.contrato_fornecedor_id)
        if cf:
            contrato_fornecedor_numero = cf.numero

    fornecedor_nome = None
    if veiculo.fornecedor_id:
        f = await session.get(Fornecedor, veiculo.fornecedor_id)
        fornecedor_nome = f.nome if f else None

    os_abertas_status = (
        OrdemServicoStatus.ABERTA,
        OrdemServicoStatus.AGUARDANDO_PECA,
        OrdemServicoStatus.EM_EXECUCAO,
        OrdemServicoStatus.AGUARDANDO_APROVACAO,
    )

    total_reservas = (
        await session.execute(
            select(func.count())
            .select_from(ResReserva)
            .where(ResReserva.veiculo_id == vid, ResReserva.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    reservas_abertas = (
        await session.execute(
            select(func.count())
            .select_from(ResReserva)
            .where(
                ResReserva.veiculo_id == vid,
                ResReserva.deleted_at.is_(None),
                ResReserva.status.in_(
                    (ReservaStatus.PENDENTE, ReservaStatus.CONFIRMADA, ReservaStatus.CHECKOUT)
                ),
            )
        )
    ).scalar_one() or 0

    total_contratos = (
        await session.execute(
            select(func.count())
            .select_from(LocContrato)
            .where(LocContrato.veiculo_id == vid, LocContrato.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    total_os = (
        await session.execute(
            select(func.count())
            .select_from(ManOrdemServico)
            .where(ManOrdemServico.veiculo_id == vid, ManOrdemServico.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    os_abertas = (
        await session.execute(
            select(func.count())
            .select_from(ManOrdemServico)
            .where(
                ManOrdemServico.veiculo_id == vid,
                ManOrdemServico.deleted_at.is_(None),
                ManOrdemServico.status.in_(os_abertas_status),
            )
        )
    ).scalar_one() or 0

    hoje = date.today()
    docs_vencidos = (
        await session.execute(
            select(func.count())
            .select_from(FrotaDocumento)
            .where(
                FrotaDocumento.veiculo_id == vid,
                FrotaDocumento.deleted_at.is_(None),
                FrotaDocumento.data_validade.is_not(None),
                FrotaDocumento.data_validade < hoje,
            )
        )
    ).scalar_one() or 0

    acessorios_count = (
        await session.execute(
            select(func.count())
            .select_from(FrotaVeiculoAcessorio)
            .where(
                FrotaVeiculoAcessorio.veiculo_id == vid,
                FrotaVeiculoAcessorio.deleted_at.is_(None),
            )
        )
    ).scalar_one() or 0

    documentos = list(
        (
            await session.execute(
                select(FrotaDocumento)
                .where(FrotaDocumento.veiculo_id == vid, FrotaDocumento.deleted_at.is_(None))
                .order_by(FrotaDocumento.data_validade.asc().nulls_last())
                .limit(12)
            )
        ).scalars().all()
    )

    fotos = list(
        (
            await session.execute(
                select(FrotaVeiculoFoto)
                .where(FrotaVeiculoFoto.veiculo_id == vid, FrotaVeiculoFoto.deleted_at.is_(None))
                .order_by(FrotaVeiculoFoto.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    telemetria = (
        await session.execute(
            select(FrotaTelemetriaDispositivo)
            .where(
                FrotaTelemetriaDispositivo.veiculo_id == vid,
                FrotaTelemetriaDispositivo.deleted_at.is_(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    reservas_recentes = list(
        (
            await session.execute(
                select(ResReserva)
                .where(ResReserva.veiculo_id == vid, ResReserva.deleted_at.is_(None))
                .order_by(ResReserva.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    contratos_recentes = list(
        (
            await session.execute(
                select(LocContrato)
                .where(LocContrato.veiculo_id == vid, LocContrato.deleted_at.is_(None))
                .order_by(LocContrato.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    ordens_recentes = list(
        (
            await session.execute(
                select(ManOrdemServico)
                .where(ManOrdemServico.veiculo_id == vid, ManOrdemServico.deleted_at.is_(None))
                .order_by(ManOrdemServico.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    return VeiculoDossier(
        veiculo=veiculo,
        categoria_nome=await _label(session, FrotaCategoria, veiculo.categoria_id),
        marca_nome=await _label(session, FrotaMarca, veiculo.marca_id),
        modelo_nome=await _label(session, FrotaModelo, veiculo.modelo_id),
        combustivel_nome=await _label(session, FrotaCombustivel, veiculo.combustivel_id),
        filial_nome=await _label(session, Filial, veiculo.filial_id),
        fornecedor_nome=fornecedor_nome,
        contrato_fornecedor_numero=contrato_fornecedor_numero,
        stats={
            "reservas": int(total_reservas),
            "reservas_abertas": int(reservas_abertas),
            "contratos": int(total_contratos),
            "ordens_servico": int(total_os),
            "os_abertas": int(os_abertas),
            "documentos_vencidos": int(docs_vencidos),
            "acessorios": int(acessorios_count),
        },
        documentos=documentos,
        fotos=fotos,
        acessorios_count=int(acessorios_count),
        telemetria=telemetria,
        reservas_recentes=reservas_recentes,
        contratos_recentes=contratos_recentes,
        ordens_recentes=ordens_recentes,
    )
