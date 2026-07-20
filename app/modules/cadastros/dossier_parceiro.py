"""Contexto da tela Dossiê do parceiro comercial."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cadastros.models_extra import Parceiro
from app.modules.cadastros.service_extra import ParceiroService
from app.modules.comercial.models import CrmCupom
from app.modules.locacoes.models import LocContrato
from app.modules.reservas.models import ResCotacao, ResReserva
from app.modules.tarifario.models import TarTabela
from app.shared.enums import CadastroStatus, CotacaoStatus, CrmCupomStatus, ReservaStatus


@dataclass
class ParceiroDossier:
    parceiro: Parceiro
    vigencia_vigente: bool = True
    stats: dict[str, int | Decimal] = field(default_factory=dict)
    reservas_recentes: list[ResReserva] = field(default_factory=list)
    cotacoes_recentes: list[ResCotacao] = field(default_factory=list)
    contratos_recentes: list[LocContrato] = field(default_factory=list)
    tabelas_tarifarias: list[TarTabela] = field(default_factory=list)
    cupons: list[CrmCupom] = field(default_factory=list)


def _vigencia_vigente(parceiro: Parceiro) -> bool:
    hoje = date.today()
    if parceiro.vigencia_inicio and parceiro.vigencia_inicio > hoje:
        return False
    if parceiro.vigencia_fim and parceiro.vigencia_fim < hoje:
        return False
    return True


async def build_parceiro_dossier(session: AsyncSession, parceiro_id: uuid.UUID) -> ParceiroDossier:
    parceiro = await ParceiroService(session).get(parceiro_id)
    pid = parceiro_id

    reservas_abertas = (
        await session.execute(
            select(func.count())
            .select_from(ResReserva)
            .where(
                ResReserva.parceiro_id == pid,
                ResReserva.deleted_at.is_(None),
                ResReserva.status.in_(
                    (ReservaStatus.PENDENTE, ReservaStatus.CONFIRMADA, ReservaStatus.CHECKOUT)
                ),
            )
        )
    ).scalar_one() or 0

    total_reservas = (
        await session.execute(
            select(func.count())
            .select_from(ResReserva)
            .where(ResReserva.parceiro_id == pid, ResReserva.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    cotacoes_abertas = (
        await session.execute(
            select(func.count())
            .select_from(ResCotacao)
            .where(
                ResCotacao.parceiro_id == pid,
                ResCotacao.deleted_at.is_(None),
                ResCotacao.status == CotacaoStatus.ABERTA,
            )
        )
    ).scalar_one() or 0

    total_cotacoes = (
        await session.execute(
            select(func.count())
            .select_from(ResCotacao)
            .where(ResCotacao.parceiro_id == pid, ResCotacao.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    contrato_filter = (
        LocContrato.deleted_at.is_(None),
        ResReserva.deleted_at.is_(None),
        ResReserva.parceiro_id == pid,
    )

    total_contratos = (
        await session.execute(
            select(func.count())
            .select_from(LocContrato)
            .join(ResReserva, LocContrato.reserva_id == ResReserva.id)
            .where(*contrato_filter)
        )
    ).scalar_one() or 0

    comissao_total = (
        await session.execute(
            select(func.coalesce(func.sum(LocContrato.valor_comissao), 0))
            .select_from(LocContrato)
            .join(ResReserva, LocContrato.reserva_id == ResReserva.id)
            .where(
                ResReserva.parceiro_id == pid,
                LocContrato.deleted_at.is_(None),
                ResReserva.deleted_at.is_(None),
            )
        )
    ).scalar_one() or Decimal("0")

    tabelas_count = (
        await session.execute(
            select(func.count())
            .select_from(TarTabela)
            .where(
                TarTabela.parceiro_id == pid,
                TarTabela.deleted_at.is_(None),
                TarTabela.status == CadastroStatus.ACTIVE,
            )
        )
    ).scalar_one() or 0

    cupons_count = (
        await session.execute(
            select(func.count())
            .select_from(CrmCupom)
            .where(
                CrmCupom.parceiro_id == pid,
                CrmCupom.deleted_at.is_(None),
                CrmCupom.status == CrmCupomStatus.ATIVO,
            )
        )
    ).scalar_one() or 0

    reservas_recentes = list(
        (
            await session.execute(
                select(ResReserva)
                .where(ResReserva.parceiro_id == pid, ResReserva.deleted_at.is_(None))
                .order_by(ResReserva.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    cotacoes_recentes = list(
        (
            await session.execute(
                select(ResCotacao)
                .where(ResCotacao.parceiro_id == pid, ResCotacao.deleted_at.is_(None))
                .order_by(ResCotacao.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    contratos_recentes = list(
        (
            await session.execute(
                select(LocContrato)
                .join(ResReserva, LocContrato.reserva_id == ResReserva.id)
                .where(*contrato_filter)
                .order_by(LocContrato.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    tabelas_tarifarias = list(
        (
            await session.execute(
                select(TarTabela)
                .where(TarTabela.parceiro_id == pid, TarTabela.deleted_at.is_(None))
                .order_by(TarTabela.vigencia_inicio.desc())
                .limit(12)
            )
        ).scalars().all()
    )

    cupons = list(
        (
            await session.execute(
                select(CrmCupom)
                .where(CrmCupom.parceiro_id == pid, CrmCupom.deleted_at.is_(None))
                .order_by(CrmCupom.created_at.desc())
                .limit(12)
            )
        ).scalars().all()
    )

    return ParceiroDossier(
        parceiro=parceiro,
        vigencia_vigente=_vigencia_vigente(parceiro),
        stats={
            "reservas": int(total_reservas),
            "reservas_abertas": int(reservas_abertas),
            "cotacoes": int(total_cotacoes),
            "cotacoes_abertas": int(cotacoes_abertas),
            "contratos": int(total_contratos),
            "comissao_total": comissao_total,
            "tabelas_ativas": int(tabelas_count),
            "cupons_ativos": int(cupons_count),
        },
        reservas_recentes=reservas_recentes,
        cotacoes_recentes=cotacoes_recentes,
        contratos_recentes=contratos_recentes,
        tabelas_tarifarias=tabelas_tarifarias,
        cupons=cupons,
    )
