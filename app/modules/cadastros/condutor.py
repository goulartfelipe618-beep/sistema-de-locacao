"""Condutor = cliente: CNH no cadastro de clientes e espelho interno em motoristas."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cadastros.models import Cliente
from app.modules.cadastros.models_extra import Motorista
from app.modules.reservas.schemas import MotoristaReservaInput
from app.shared.enums import CadastroStatus, MotoristaCnhStatus, MotoristaVinculo


def refresh_cnh_status(cliente: Cliente, *, today: date | None = None) -> None:
    """Atualiza status da CNH com base na validade."""
    ref = today or date.today()
    if cliente.cnh_validade and cliente.cnh_validade < ref:
        cliente.cnh_status = MotoristaCnhStatus.VENCIDA
    elif cliente.cnh_status == MotoristaCnhStatus.VENCIDA and cliente.cnh_validade:
        if cliente.cnh_validade >= ref:
            cliente.cnh_status = MotoristaCnhStatus.REGULAR


def cliente_tem_cnh_valida(cliente: Cliente) -> bool:
    refresh_cnh_status(cliente)
    if not cliente.cnh_numero:
        return False
    return cliente.cnh_status not in (
        MotoristaCnhStatus.VENCIDA,
        MotoristaCnhStatus.SUSPENSA,
        MotoristaCnhStatus.CASSADA,
    )


async def sync_shadow_motorista(session: AsyncSession, cliente: Cliente) -> Motorista | None:
    """Mantém registro técnico em motoristas (FKs legadas) espelhando o cliente."""
    if not cliente.cnh_numero:
        return None

    stmt = (
        select(Motorista)
        .where(
            Motorista.tenant_id == cliente.tenant_id,
            Motorista.cliente_id == cliente.id,
            Motorista.deleted_at.is_(None),
        )
        .limit(1)
    )
    motorista = (await session.execute(stmt)).scalar_one_or_none()

    if motorista is None and cliente.cpf:
        stmt_cpf = (
            select(Motorista)
            .where(
                Motorista.tenant_id == cliente.tenant_id,
                Motorista.cpf == cliente.cpf,
                Motorista.deleted_at.is_(None),
            )
            .limit(1)
        )
        motorista = (await session.execute(stmt_cpf)).scalar_one_or_none()

    if motorista is None:
        motorista = Motorista(
            tenant_id=cliente.tenant_id,
            cliente_id=cliente.id,
            vinculo=MotoristaVinculo.CLIENTE,
            status=CadastroStatus.ACTIVE,
            nome=cliente.nome,
            cpf=cliente.cpf,
            email=cliente.email,
            telefone=cliente.telefone,
            celular=cliente.celular,
            data_nascimento=cliente.data_nascimento,
        )
        session.add(motorista)

    motorista.cliente_id = cliente.id
    motorista.vinculo = MotoristaVinculo.CLIENTE
    motorista.nome = cliente.nome
    motorista.cpf = cliente.cpf
    motorista.email = cliente.email
    motorista.telefone = cliente.telefone
    motorista.celular = cliente.celular
    motorista.data_nascimento = cliente.data_nascimento
    motorista.cnh_numero = cliente.cnh_numero
    motorista.cnh_categoria = cliente.cnh_categoria
    motorista.cnh_emissao = cliente.cnh_emissao
    motorista.cnh_validade = cliente.cnh_validade
    motorista.cnh_orgao = cliente.cnh_orgao
    motorista.cnh_status = cliente.cnh_status
    motorista.cnh_pontuacao = cliente.cnh_pontuacao
    motorista.status = (
        CadastroStatus.ACTIVE
        if cliente.status.value == "active"
        else CadastroStatus.INACTIVE
    )
    await session.flush()
    return motorista


async def motorista_inputs_for_cliente(
    session: AsyncSession, cliente_id: uuid.UUID
) -> list[MotoristaReservaInput]:
    """Retorna condutor(es) da reserva/contrato a partir do cliente."""
    cliente = await session.get(Cliente, cliente_id)
    if cliente is None or cliente.deleted_at is not None:
        return []
    refresh_cnh_status(cliente)
    motorista = await sync_shadow_motorista(session, cliente)
    if motorista is None:
        return []
    return [MotoristaReservaInput(motorista_id=motorista.id, principal=True)]


async def ensure_contrato_motoristas_from_cliente(session: AsyncSession, contrato) -> None:
    """Vincula condutor ao contrato a partir do cliente quando ainda não há motoristas."""
    from app.modules.locacoes.models import LocContratoMotorista

    stmt = select(LocContratoMotorista).where(
        LocContratoMotorista.contrato_id == contrato.id,
        LocContratoMotorista.deleted_at.is_(None),
    )
    if (await session.execute(stmt)).scalars().first():
        return

    inputs = await motorista_inputs_for_cliente(session, contrato.cliente_id)
    for inp in inputs:
        session.add(
            LocContratoMotorista(
                tenant_id=contrato.tenant_id,
                contrato_id=contrato.id,
                motorista_id=inp.motorista_id,
                principal=inp.principal,
            )
        )
    if inputs:
        await session.flush()

