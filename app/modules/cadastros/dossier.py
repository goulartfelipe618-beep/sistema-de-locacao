"""Contexto da tela Dossiê do cliente."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.cadastros.condutor import cliente_tem_cnh_valida, refresh_cnh_status
from app.modules.cadastros.cliente_documentos import ClienteDocumentoService
from app.modules.cadastros.models import Cliente, ClienteDocumento
from app.modules.cadastros.repository import TabelaAuxiliarRepository
from app.modules.cadastros.service import ClienteService
from app.modules.financeiro.models import FinContaReceber
from app.modules.locacoes.models import LocContrato
from app.modules.reservas.models import ResReserva
from app.modules.tenants.service import FilialService
from app.shared.entity_impact import cliente_impact
from app.shared.enums import ReservaStatus, TituloStatus


@dataclass
class ClienteDossier:
    cliente: Cliente
    categoria_label: str | None = None
    cnh_categoria_label: str | None = None
    filial_nome: str | None = None
    cnh_valida: bool = False
    cnh_vencendo: bool = False
    stats: dict[str, int | Decimal] = field(default_factory=dict)
    contratos_recentes: list[LocContrato] = field(default_factory=list)
    reservas_recentes: list[ResReserva] = field(default_factory=list)
    titulos_recentes: list[FinContaReceber] = field(default_factory=list)
    documentos: dict[str, ClienteDocumento] = field(default_factory=dict)
    impacto: dict = field(default_factory=dict)


async def build_cliente_dossier(session: AsyncSession, cliente_id: uuid.UUID) -> ClienteDossier:
    svc = ClienteService(session)
    cliente = await svc.get(cliente_id)
    refresh_cnh_status(cliente)

    aux_repo = TabelaAuxiliarRepository(session)

    categoria_label = None
    if cliente.categoria_codigo:
        item = await aux_repo.get_by_grupo_codigo("categoria_cliente", cliente.categoria_codigo)
        categoria_label = item.descricao if item else cliente.categoria_codigo

    cnh_categoria_label = None
    if cliente.cnh_categoria:
        item = await aux_repo.get_by_grupo_codigo("cnh_categoria", cliente.cnh_categoria.lower())
        cnh_categoria_label = item.descricao if item else cliente.cnh_categoria

    filial_nome = None
    if cliente.filial_id:
        try:
            filial = await FilialService(session).get_filial(cliente.filial_id)
            filial_nome = filial.name
        except NotFoundError:
            filial_nome = None

    cnh_vencendo = False
    if cliente.cnh_validade:
        limite = date.today().toordinal() + 30
        cnh_vencendo = cliente.cnh_validade.toordinal() <= limite

    titulos_pendentes = (
        await session.execute(
            select(func.count())
            .select_from(FinContaReceber)
            .where(
                FinContaReceber.cliente_id == cliente_id,
                FinContaReceber.deleted_at.is_(None),
                FinContaReceber.status.in_(
                    (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
                ),
            )
        )
    ).scalar_one() or 0

    saldo_aberto = (
        await session.execute(
            select(func.coalesce(func.sum(FinContaReceber.valor_saldo), 0))
            .select_from(FinContaReceber)
            .where(
                FinContaReceber.cliente_id == cliente_id,
                FinContaReceber.deleted_at.is_(None),
                FinContaReceber.status.in_(
                    (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
                ),
            )
        )
    ).scalar_one() or Decimal("0")

    total_contratos = (
        await session.execute(
            select(func.count())
            .select_from(LocContrato)
            .where(LocContrato.cliente_id == cliente_id, LocContrato.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    reservas_abertas = (
        await session.execute(
            select(func.count())
            .select_from(ResReserva)
            .where(
                ResReserva.cliente_id == cliente_id,
                ResReserva.deleted_at.is_(None),
                ResReserva.status.in_(
                    (ReservaStatus.PENDENTE, ReservaStatus.CONFIRMADA, ReservaStatus.CHECKOUT)
                ),
            )
        )
    ).scalar_one() or 0

    contratos_recentes = list(
        (
            await session.execute(
                select(LocContrato)
                .where(LocContrato.cliente_id == cliente_id, LocContrato.deleted_at.is_(None))
                .order_by(LocContrato.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    reservas_recentes = list(
        (
            await session.execute(
                select(ResReserva)
                .where(ResReserva.cliente_id == cliente_id, ResReserva.deleted_at.is_(None))
                .order_by(ResReserva.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    titulos_recentes = list(
        (
            await session.execute(
                select(FinContaReceber)
                .where(FinContaReceber.cliente_id == cliente_id, FinContaReceber.deleted_at.is_(None))
                .order_by(FinContaReceber.vencimento.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    return ClienteDossier(
        cliente=cliente,
        categoria_label=categoria_label,
        cnh_categoria_label=cnh_categoria_label,
        filial_nome=filial_nome,
        cnh_valida=cliente_tem_cnh_valida(cliente),
        cnh_vencendo=bool(
            cnh_vencendo
            and cliente.cnh_validade
            and cliente.cnh_validade >= date.today()
        ),
        stats={
            "contratos": int(total_contratos),
            "reservas_abertas": int(reservas_abertas),
            "titulos_pendentes": int(titulos_pendentes),
            "saldo_aberto": saldo_aberto,
        },
        contratos_recentes=contratos_recentes,
        reservas_recentes=reservas_recentes,
        titulos_recentes=titulos_recentes,
        documentos=await ClienteDocumentoService(session).map_by_tipo(cliente_id),
        impacto=await cliente_impact(session, cliente_id),
    )
