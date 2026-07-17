"""Consulta de impacto downstream ao excluir/inativar entidades."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.financeiro.models import FinContaReceber
from app.modules.locacoes.models import LocContrato, LocContratoMotorista
from app.modules.manutencao.models import ManOrdemServico
from app.modules.reservas.models import ResReserva, ResReservaMotorista
from app.shared.enums import ContratoStatus, OrdemServicoStatus, ReservaStatus, TituloStatus

_OS_ABERTAS = (
    OrdemServicoStatus.ABERTA,
    OrdemServicoStatus.AGUARDANDO_PECA,
    OrdemServicoStatus.EM_EXECUCAO,
    OrdemServicoStatus.AGUARDANDO_APROVACAO,
)

_CONTRATO_ATIVOS = (
    ContratoStatus.RASCUNHO,
    ContratoStatus.AGUARDANDO_CHECKOUT,
    ContratoStatus.ATIVO,
    ContratoStatus.AGUARDANDO_CHECKIN,
)

_RESERVA_ABERTAS = (
    ReservaStatus.PENDENTE,
    ReservaStatus.CONFIRMADA,
    ReservaStatus.CHECKOUT,
)


async def _count(session: AsyncSession, stmt) -> int:
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def cliente_impact(session: AsyncSession, cliente_id: uuid.UUID) -> dict[str, Any]:
    contratos = await _count(
        session,
        select(func.count())
        .select_from(LocContrato)
        .where(
            LocContrato.cliente_id == cliente_id,
            LocContrato.deleted_at.is_(None),
            LocContrato.status.in_(_CONTRATO_ATIVOS),
        ),
    )
    reservas = await _count(
        session,
        select(func.count())
        .select_from(ResReserva)
        .where(
            ResReserva.cliente_id == cliente_id,
            ResReserva.deleted_at.is_(None),
            ResReserva.status.in_(_RESERVA_ABERTAS),
        ),
    )
    titulos = await _count(
        session,
        select(func.count())
        .select_from(FinContaReceber)
        .where(
            FinContaReceber.cliente_id == cliente_id,
            FinContaReceber.deleted_at.is_(None),
            FinContaReceber.status.in_(
                (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
            ),
        ),
    )
    blocked = contratos > 0 or reservas > 0
    details = [
        {"label": "Contratos ativos", "count": contratos},
        {"label": "Reservas abertas", "count": reservas},
        {"label": "Títulos em aberto", "count": titulos},
    ]
    return {
        "entity": "cliente",
        "blocked": blocked,
        "can_proceed": not blocked,
        "summary": _build_summary("cliente", details, blocked),
        "details": details,
    }


async def motorista_impact(session: AsyncSession, motorista_id: uuid.UUID) -> dict[str, Any]:
    reservas = await _count(
        session,
        select(func.count())
        .select_from(ResReservaMotorista)
        .join(ResReserva, ResReservaMotorista.reserva_id == ResReserva.id)
        .where(
            ResReservaMotorista.motorista_id == motorista_id,
            ResReservaMotorista.deleted_at.is_(None),
            ResReserva.deleted_at.is_(None),
            ResReserva.status.in_(_RESERVA_ABERTAS),
        ),
    )
    contratos = await _count(
        session,
        select(func.count())
        .select_from(LocContratoMotorista)
        .join(LocContrato, LocContratoMotorista.contrato_id == LocContrato.id)
        .where(
            LocContratoMotorista.motorista_id == motorista_id,
            LocContratoMotorista.deleted_at.is_(None),
            LocContrato.deleted_at.is_(None),
            LocContrato.status.in_(_CONTRATO_ATIVOS),
        ),
    )
    blocked = reservas > 0 or contratos > 0
    details = [
        {"label": "Reservas abertas", "count": reservas},
        {"label": "Contratos ativos", "count": contratos},
    ]
    return {
        "entity": "motorista",
        "blocked": blocked,
        "can_proceed": not blocked,
        "summary": _build_summary("motorista", details, blocked),
        "details": details,
    }


async def veiculo_impact(session: AsyncSession, veiculo_id: uuid.UUID) -> dict[str, Any]:
    contratos = await _count(
        session,
        select(func.count())
        .select_from(LocContrato)
        .where(
            LocContrato.veiculo_id == veiculo_id,
            LocContrato.deleted_at.is_(None),
            LocContrato.status.in_(_CONTRATO_ATIVOS),
        ),
    )
    reservas = await _count(
        session,
        select(func.count())
        .select_from(ResReserva)
        .where(
            ResReserva.veiculo_id == veiculo_id,
            ResReserva.deleted_at.is_(None),
            ResReserva.status.in_(_RESERVA_ABERTAS),
        ),
    )
    os_abertas = await _count(
        session,
        select(func.count())
        .select_from(ManOrdemServico)
        .where(
            ManOrdemServico.veiculo_id == veiculo_id,
            ManOrdemServico.deleted_at.is_(None),
            ManOrdemServico.status.in_(_OS_ABERTAS),
        ),
    )
    blocked = contratos > 0 or reservas > 0 or os_abertas > 0
    details = [
        {"label": "Contratos ativos", "count": contratos},
        {"label": "Reservas abertas", "count": reservas},
        {"label": "OS em aberto", "count": os_abertas},
    ]
    return {
        "entity": "veiculo",
        "blocked": blocked,
        "can_proceed": not blocked,
        "summary": _build_summary("veículo", details, blocked),
        "details": details,
    }


def _build_summary(entity_label: str, details: list[dict[str, Any]], blocked: bool) -> str:
    parts = [f"{d['count']} {d['label'].lower()}" for d in details if d["count"] > 0]
    if blocked:
        base = f"Não é possível prosseguir: o {entity_label} possui "
        return base + (", ".join(parts) if parts else "vínculos ativos") + "."
    if parts:
        return f"Atenção: existem {', '.join(parts)}. A ação pode desvincular registros."
    return f"Nenhum vínculo crítico encontrado para este {entity_label}."
