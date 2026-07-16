"""Serviços de negócio do módulo Locações (§6.1–6.7)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.cadastros.models_extra import Motorista
from app.modules.frota.models import FrotaCombustivel, FrotaDocumento, FrotaModelo
from app.modules.frota.service import VeiculoService
from app.modules.locacoes.models import (
    LocAvaria,
    LocAvariaFoto,
    LocContrato,
    LocContratoAditivo,
    LocContratoItem,
    LocContratoMotorista,
    LocMulta,
    LocVistoria,
    LocVistoriaFoto,
)
from app.modules.locacoes.schemas import (
    AvariaCheckinInput,
    AvariaCreate,
    AvariaResponsabilidadeInput,
    AvariaUpdate,
    CheckoutConcluirInput,
    CheckinConcluirInput,
    ContratoCancelInput,
    ContratoCreate,
    ContratoUpdate,
    MultaCreate,
    MultaUpdate,
    ReabrirInput,
    RenovacaoInput,
)
from app.modules.manutencao.schemas import OrdemServicoCreate
from app.modules.manutencao.service import OrdemServicoService
from app.modules.reservas.models import ResReserva, ResReservaItem, ResReservaMotorista
from app.modules.reservas.service import DisponibilidadeService, ReservaService
from app.modules.tarifario.schemas import PricingLineItem, PricingQuoteInput
from app.modules.tarifario.service import PricingService
from app.shared.enums import (
    AuditAction,
    AvariaOrigem,
    AvariaResponsabilidade,
    AvariaSeveridade,
    AvariaStatus,
    ContratoStatus,
    CorretivaCausa,
    CorretivaResponsavel,
    DocumentoVeiculoStatus,
    MotoristaCnhStatus,
    MultaStatus,
    OrdemServicoOrigem,
    OrdemServicoTipo,
    ReservaItemTipo,
    ReservaOrigem,
    ReservaStatus,
    TarifarioCanal,
    VeiculoStatus,
    VistoriaTipo,
)
from app.shared.repository import BaseRepository

_MONEY = Decimal("0.01")
_ZERO = Decimal("0")
_DEFAULT_TANK_LITERS = Decimal("50")
_CNH_INVALID = {
    MotoristaCnhStatus.VENCIDA,
    MotoristaCnhStatus.SUSPENSA,
    MotoristaCnhStatus.CASSADA,
}
_EDITABLE_CONTRATO_STATUSES = {ContratoStatus.RASCUNHO}
_BLOCKING_CONTRATO_STATUSES = {
    ContratoStatus.AGUARDANDO_CHECKOUT,
    ContratoStatus.ATIVO,
    ContratoStatus.AGUARDANDO_CHECKIN,
}
_CHECKOUT_ALLOWED = {
    ContratoStatus.RASCUNHO,
    ContratoStatus.AGUARDANDO_CHECKOUT,
}
_CHECKIN_ALLOWED = {
    ContratoStatus.ATIVO,
    ContratoStatus.AGUARDANDO_CHECKIN,
}

CONTRATO_TRANSITIONS: dict[ContratoStatus, set[ContratoStatus]] = {
    ContratoStatus.RASCUNHO: {
        ContratoStatus.AGUARDANDO_CHECKOUT,
        ContratoStatus.CANCELADO,
    },
    ContratoStatus.AGUARDANDO_CHECKOUT: {
        ContratoStatus.ATIVO,
        ContratoStatus.CANCELADO,
    },
    ContratoStatus.ATIVO: {ContratoStatus.AGUARDANDO_CHECKIN},
    ContratoStatus.AGUARDANDO_CHECKIN: {
        ContratoStatus.ENCERRADO,
        ContratoStatus.ENCERRADO_PENDENCIA,
    },
    ContratoStatus.ENCERRADO: {ContratoStatus.AGUARDANDO_CHECKIN},
    ContratoStatus.ENCERRADO_PENDENCIA: {
        ContratoStatus.ENCERRADO,
        ContratoStatus.AGUARDANDO_CHECKIN,
    },
    ContratoStatus.CANCELADO: set(),
}

_ORIGEM_CANAL: dict[ReservaOrigem, TarifarioCanal] = {
    ReservaOrigem.BALCAO: TarifarioCanal.BALCAO,
    ReservaOrigem.WEBSITE: TarifarioCanal.SITE,
    ReservaOrigem.APP: TarifarioCanal.APP,
    ReservaOrigem.PARCEIRO: TarifarioCanal.PARCEIRO,
    ReservaOrigem.TELEFONE: TarifarioCanal.TELEFONE,
}

_ITEM_TIPO_MAP = {
    "taxa": ReservaItemTipo.TAXA,
    "protecao": ReservaItemTipo.PROTECAO,
    "acessorio": ReservaItemTipo.ACESSORIO,
}


# ---------------------------------------------------------------- Repositories
class ContratoRepository(BaseRepository[LocContrato]):
    model = LocContrato

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(LocContrato)
            .where(
                LocContrato.tenant_id == tenant_id,
                LocContrato.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: ContratoStatus | None = None,
        statuses: set[ContratoStatus] | None = None,
        cliente_id: uuid.UUID | None = None,
        veiculo_id: uuid.UUID | None = None,
        reserva_id: uuid.UUID | None = None,
        pendencia_financeira: bool | None = None,
        search: str | None = None,
    ) -> Select[tuple[LocContrato]]:
        stmt = self._base_query().order_by(LocContrato.created_at.desc())
        if status:
            stmt = stmt.where(LocContrato.status == status)
        if statuses:
            stmt = stmt.where(LocContrato.status.in_(statuses))
        if cliente_id:
            stmt = stmt.where(LocContrato.cliente_id == cliente_id)
        if veiculo_id:
            stmt = stmt.where(LocContrato.veiculo_id == veiculo_id)
        if reserva_id:
            stmt = stmt.where(LocContrato.reserva_id == reserva_id)
        if pendencia_financeira is not None:
            stmt = stmt.where(LocContrato.pendencia_financeira == pendencia_financeira)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(LocContrato.numero).like(term))
        return stmt

    async def overlapping_for_period(
        self,
        *,
        inicio: datetime,
        fim: datetime,
        veiculo_id: uuid.UUID,
        statuses: set[ContratoStatus],
        exclude_contrato_id: uuid.UUID | None = None,
    ) -> list[LocContrato]:
        stmt = self._base_query().where(
            LocContrato.veiculo_id == veiculo_id,
            LocContrato.status.in_(statuses),
            LocContrato.retirada_prevista_em < fim,
            LocContrato.devolucao_prevista_em > inicio,
        )
        if exclude_contrato_id:
            stmt = stmt.where(LocContrato.id != exclude_contrato_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def active_at_moment(
        self,
        *,
        veiculo_id: uuid.UUID,
        momento: datetime,
    ) -> list[LocContrato]:
        stmt = self._base_query().where(
            LocContrato.veiculo_id == veiculo_id,
            LocContrato.status.in_(
                {ContratoStatus.ATIVO, ContratoStatus.AGUARDANDO_CHECKIN}
            ),
            LocContrato.checkout_em.is_not(None),
            LocContrato.checkout_em <= momento,
            or_(
                LocContrato.checkin_em.is_(None),
                LocContrato.checkin_em >= momento,
            ),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ContratoItemRepository(BaseRepository[LocContratoItem]):
    model = LocContratoItem

    async def delete_by_contrato(self, contrato_id: uuid.UUID) -> None:
        stmt = select(LocContratoItem).where(
            LocContratoItem.contrato_id == contrato_id,
            LocContratoItem.deleted_at.is_(None),
        )
        for row in (await self.session.execute(stmt)).scalars().all():
            await self.delete(row)


class ContratoMotoristaRepository(BaseRepository[LocContratoMotorista]):
    model = LocContratoMotorista

    async def delete_by_contrato(self, contrato_id: uuid.UUID) -> None:
        stmt = select(LocContratoMotorista).where(
            LocContratoMotorista.contrato_id == contrato_id,
            LocContratoMotorista.deleted_at.is_(None),
        )
        for row in (await self.session.execute(stmt)).scalars().all():
            await self.delete(row)


class ContratoAditivoRepository(BaseRepository[LocContratoAditivo]):
    model = LocContratoAditivo


class VistoriaRepository(BaseRepository[LocVistoria]):
    model = LocVistoria


class VistoriaFotoRepository(BaseRepository[LocVistoriaFoto]):
    model = LocVistoriaFoto


class AvariaRepository(BaseRepository[LocAvaria]):
    model = LocAvaria

    def list_query(
        self,
        *,
        veiculo_id: uuid.UUID | None = None,
        contrato_id: uuid.UUID | None = None,
        status: AvariaStatus | None = None,
    ) -> Select[tuple[LocAvaria]]:
        stmt = self._base_query().order_by(LocAvaria.created_at.desc())
        if veiculo_id:
            stmt = stmt.where(LocAvaria.veiculo_id == veiculo_id)
        if contrato_id:
            stmt = stmt.where(LocAvaria.contrato_id == contrato_id)
        if status:
            stmt = stmt.where(LocAvaria.status == status)
        return stmt


class AvariaFotoRepository(BaseRepository[LocAvariaFoto]):
    model = LocAvariaFoto


class MultaRepository(BaseRepository[LocMulta]):
    model = LocMulta

    def list_query(
        self,
        *,
        veiculo_id: uuid.UUID | None = None,
        contrato_id: uuid.UUID | None = None,
        cliente_id: uuid.UUID | None = None,
        status: MultaStatus | None = None,
    ) -> Select[tuple[LocMulta]]:
        stmt = self._base_query().order_by(LocMulta.ocorrido_em.desc())
        if veiculo_id:
            stmt = stmt.where(LocMulta.veiculo_id == veiculo_id)
        if contrato_id:
            stmt = stmt.where(LocMulta.contrato_id == contrato_id)
        if cliente_id:
            stmt = stmt.where(LocMulta.cliente_id == cliente_id)
        if status:
            stmt = stmt.where(LocMulta.status == status)
        return stmt


# --------------------------------------------------------------------- Helpers
def _money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY)


def _origem_canal(origem: ReservaOrigem) -> TarifarioCanal:
    return _ORIGEM_CANAL.get(origem, TarifarioCanal.BALCAO)


def _assert_transition(current: ContratoStatus, new: ContratoStatus) -> None:
    allowed = CONTRATO_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise BusinessRuleError(
            f"Transição inválida: {current.value} → {new.value}.",
            code="transicao_invalida",
        )


def _pricing_to_contrato_fields(pricing, *, desconto: Decimal = _ZERO, caucao: Decimal = _ZERO) -> dict:
    subtotal = _money(pricing.subtotal_diarias + pricing.temporada_ajuste)
    valor_total = _money(max(_ZERO, pricing.total - desconto))
    return {
        "diaria_unitaria": pricing.diaria_unitaria,
        "dias": pricing.dias,
        "subtotal": subtotal,
        "total_taxas": pricing.subtotal_taxas,
        "total_protecoes": pricing.subtotal_protecoes,
        "total_acessorios": pricing.subtotal_acessorios,
        "desconto": desconto,
        "caucao": caucao,
        "valor_total": valor_total,
        "pricing_snapshot": json.dumps(pricing.snapshot, ensure_ascii=False),
    }


def _line_to_item(
    contrato_id: uuid.UUID, tenant_id: uuid.UUID, line: PricingLineItem
) -> LocContratoItem:
    tipo = _ITEM_TIPO_MAP.get(line.tipo, ReservaItemTipo.TAXA)
    return LocContratoItem(
        tenant_id=tenant_id,
        contrato_id=contrato_id,
        tipo=tipo,
        referencia_id=line.referencia_id,
        descricao=line.nome,
        quantidade=line.quantidade,
        valor_unitario=line.valor_unitario,
        valor_total=line.valor_total,
    )


def _reserva_item_to_contrato_item(
    contrato_id: uuid.UUID, tenant_id: uuid.UUID, item: ResReservaItem
) -> LocContratoItem:
    return LocContratoItem(
        tenant_id=tenant_id,
        contrato_id=contrato_id,
        tipo=item.tipo,
        referencia_id=item.referencia_id,
        descricao=item.descricao,
        quantidade=item.quantidade,
        valor_unitario=item.valor_unitario,
        valor_total=item.valor_total,
    )


# --------------------------------------------------------------------- Services
class ContratoService:
    """Gestão de contratos de locação (§6.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ContratoRepository(session)
        self.item_repo = ContratoItemRepository(session)
        self.motorista_repo = ContratoMotoristaRepository(session)
        self.pricing = PricingService(session)
        self.veiculo_svc = VeiculoService(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"LOC-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: ContratoStatus | None = None,
        statuses: set[ContratoStatus] | None = None,
        cliente_id: uuid.UUID | None = None,
        veiculo_id: uuid.UUID | None = None,
        reserva_id: uuid.UUID | None = None,
        pendencia_financeira: bool | None = None,
        search: str | None = None,
    ) -> Page[LocContrato]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(
                status=status,
                statuses=statuses,
                cliente_id=cliente_id,
                veiculo_id=veiculo_id,
                reserva_id=reserva_id,
                pendencia_financeira=pendencia_financeira,
                search=search,
            ),
        )

    async def get(self, contrato_id: uuid.UUID) -> LocContrato:
        item = await self.repo.get(contrato_id)
        if item is None:
            raise NotFoundError("Contrato não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: ContratoCreate) -> LocContrato:
        await self.veiculo_svc.get(data.veiculo_id)

        pricing_input = PricingQuoteInput(
            tenant_id=tenant_id,
            filial_id=data.filial_retirada_id,
            categoria_id=data.categoria_id,
            canal=_origem_canal(data.origem),
            retirada_em=data.retirada_prevista_em,
            devolucao_em=data.devolucao_prevista_em,
            veiculo_id=data.veiculo_id,
            cliente_id=data.cliente_id,
            parceiro_id=data.parceiro_id,
            protecao_ids=data.protecao_ids,
            taxa_ids=data.taxa_ids,
            acessorio_ids=data.acessorio_ids,
            one_way=data.filial_retirada_id != data.filial_devolucao_id,
        )
        quote = await self.pricing.calcular(pricing_input)
        fields = _pricing_to_contrato_fields(
            quote, desconto=data.desconto, caucao=data.caucao
        )

        contrato = LocContrato(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            status=ContratoStatus.RASCUNHO,
            cliente_id=data.cliente_id,
            veiculo_id=data.veiculo_id,
            categoria_id=data.categoria_id,
            filial_retirada_id=data.filial_retirada_id,
            filial_devolucao_id=data.filial_devolucao_id,
            retirada_prevista_em=data.retirada_prevista_em,
            devolucao_prevista_em=data.devolucao_prevista_em,
            forma_pagamento=data.forma_pagamento,
            condicao=data.condicao,
            clausulas_combustivel=data.clausulas_combustivel,
            observacoes=data.observacoes,
            **fields,
        )
        self.repo.add(contrato)
        await self.repo.flush()

        await self._sync_itens_from_quote(tenant_id, contrato.id, quote)
        await self._sync_motoristas(tenant_id, contrato.id, data.motoristas)

        await audit_service.record(
            AuditAction.CREATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=f"Contrato criado (balcão): {contrato.numero}",
        )
        return contrato

    async def from_reserva(self, reserva_id: uuid.UUID) -> LocContrato:
        stmt = select(ResReserva).where(
            ResReserva.id == reserva_id,
            ResReserva.deleted_at.is_(None),
        )
        reserva = (await self.session.execute(stmt)).scalar_one_or_none()
        if reserva is None:
            raise NotFoundError("Reserva não encontrada.")
        if reserva.status != ReservaStatus.CONFIRMADA:
            raise BusinessRuleError(
                "Somente reservas confirmadas geram contrato.",
                code="reserva_nao_confirmada",
            )
        if not reserva.veiculo_id:
            raise BusinessRuleError(
                "Reserva deve ter veículo alocado para gerar contrato.",
                code="reserva_sem_veiculo",
            )

        existing = await self.repo.list_query(reserva_id=reserva_id)
        dup = (await self.session.execute(existing.limit(1))).scalar_one_or_none()
        if dup:
            raise ConflictError(
                "Já existe contrato vinculado a esta reserva.",
                code="contrato_duplicado",
            )

        contrato = LocContrato(
            tenant_id=reserva.tenant_id,
            numero=await self.next_numero(reserva.tenant_id),
            status=ContratoStatus.AGUARDANDO_CHECKOUT,
            reserva_id=reserva.id,
            cliente_id=reserva.cliente_id,
            veiculo_id=reserva.veiculo_id,
            categoria_id=reserva.categoria_id,
            filial_retirada_id=reserva.filial_retirada_id,
            filial_devolucao_id=reserva.filial_devolucao_id,
            retirada_prevista_em=reserva.retirada_em,
            devolucao_prevista_em=reserva.devolucao_em,
            diaria_unitaria=reserva.diaria_unitaria,
            dias=reserva.dias,
            subtotal=reserva.subtotal,
            total_taxas=reserva.total_taxas,
            total_protecoes=reserva.total_protecoes,
            total_acessorios=reserva.total_acessorios,
            desconto=reserva.desconto,
            caucao=_ZERO,
            valor_total=reserva.valor_total,
            forma_pagamento=reserva.forma_pagamento_prevista,
            pricing_snapshot=reserva.pricing_snapshot,
            politica_snapshot=reserva.politica_snapshot,
            observacoes=reserva.observacoes,
        )
        self.repo.add(contrato)
        await self.repo.flush()

        await self._copy_itens_from_reserva(reserva.tenant_id, contrato.id, reserva.id)
        await self._copy_motoristas_from_reserva(reserva.tenant_id, contrato.id, reserva.id)

        await audit_service.record(
            AuditAction.CREATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=f"Contrato gerado da reserva {reserva.numero}: {contrato.numero}",
        )
        return contrato

    async def update(self, contrato_id: uuid.UUID, data: ContratoUpdate) -> LocContrato:
        contrato = await self.get(contrato_id)
        if contrato.status not in _EDITABLE_CONTRATO_STATUSES:
            raise BusinessRuleError("Somente contratos em rascunho podem ser editados.")

        payload = data.model_dump(exclude_unset=True)
        motoristas = payload.pop("motoristas", None)
        protecao_ids = payload.pop("protecao_ids", None)
        taxa_ids = payload.pop("taxa_ids", None)
        acessorio_ids = payload.pop("acessorio_ids", None)
        desconto = payload.pop("desconto", None)

        for key, value in payload.items():
            setattr(contrato, key, value)

        if any(
            k in data.model_dump(exclude_unset=True)
            for k in (
                "retirada_prevista_em",
                "devolucao_prevista_em",
                "filial_retirada_id",
                "filial_devolucao_id",
            )
        ) or protecao_ids is not None or taxa_ids is not None or acessorio_ids is not None:
            create_like = ContratoCreate(
                cliente_id=contrato.cliente_id,
                veiculo_id=contrato.veiculo_id,
                categoria_id=contrato.categoria_id,
                filial_retirada_id=contrato.filial_retirada_id,
                filial_devolucao_id=contrato.filial_devolucao_id,
                retirada_prevista_em=contrato.retirada_prevista_em,
                devolucao_prevista_em=contrato.devolucao_prevista_em,
                protecao_ids=protecao_ids or [],
                taxa_ids=taxa_ids or [],
                acessorio_ids=acessorio_ids or [],
                desconto=desconto if desconto is not None else contrato.desconto,
                caucao=contrato.caucao,
            )
            pricing_input = PricingQuoteInput(
                tenant_id=contrato.tenant_id,
                filial_id=create_like.filial_retirada_id,
                categoria_id=create_like.categoria_id,
                canal=TarifarioCanal.BALCAO,
                retirada_em=create_like.retirada_prevista_em,
                devolucao_em=create_like.devolucao_prevista_em,
                veiculo_id=create_like.veiculo_id,
                cliente_id=create_like.cliente_id,
                protecao_ids=create_like.protecao_ids,
                taxa_ids=create_like.taxa_ids,
                acessorio_ids=create_like.acessorio_ids,
                one_way=create_like.filial_retirada_id != create_like.filial_devolucao_id,
            )
            quote = await self.pricing.calcular(pricing_input)
            fields = _pricing_to_contrato_fields(
                quote,
                desconto=desconto if desconto is not None else contrato.desconto,
                caucao=contrato.caucao,
            )
            for key, value in fields.items():
                setattr(contrato, key, value)
            await self.item_repo.delete_by_contrato(contrato.id)
            await self._sync_itens_from_quote(contrato.tenant_id, contrato.id, quote)

        if motoristas is not None:
            await self.motorista_repo.delete_by_contrato(contrato.id)
            await self._sync_motoristas(contrato.tenant_id, contrato.id, motoristas)

        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=f"Contrato atualizado: {contrato.numero}",
        )
        return contrato

    async def cancelar(
        self, contrato_id: uuid.UUID, data: ContratoCancelInput
    ) -> LocContrato:
        contrato = await self.get(contrato_id)
        if contrato.status in {
            ContratoStatus.ENCERRADO,
            ContratoStatus.ENCERRADO_PENDENCIA,
            ContratoStatus.CANCELADO,
            ContratoStatus.ATIVO,
        }:
            raise BusinessRuleError("Contrato não pode ser cancelado neste status.")

        _assert_transition(contrato.status, ContratoStatus.CANCELADO)
        contrato.status = ContratoStatus.CANCELADO
        contrato.observacoes = (
            f"{contrato.observacoes or ''}\nCancelado: {data.motivo}".strip()
        )
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=f"Contrato cancelado: {contrato.numero}",
        )
        return contrato

    async def transition_to(
        self, contrato_id: uuid.UUID, new_status: ContratoStatus
    ) -> LocContrato:
        contrato = await self.get(contrato_id)
        _assert_transition(contrato.status, new_status)
        contrato.status = new_status
        await self.repo.flush()
        return contrato

    async def _sync_itens_from_quote(
        self, tenant_id: uuid.UUID, contrato_id: uuid.UUID, quote
    ) -> None:
        for line in quote.taxas + quote.protecoes + quote.acessorios:
            self.item_repo.add(_line_to_item(contrato_id, tenant_id, line))
        await self.item_repo.flush()

    async def _sync_motoristas(
        self, tenant_id: uuid.UUID, contrato_id: uuid.UUID, motoristas
    ) -> None:
        if not motoristas:
            return
        has_principal = any(m.principal for m in motoristas)
        for idx, mot in enumerate(motoristas):
            principal = mot.principal or (not has_principal and idx == 0)
            self.motorista_repo.add(
                LocContratoMotorista(
                    tenant_id=tenant_id,
                    contrato_id=contrato_id,
                    motorista_id=mot.motorista_id,
                    principal=principal,
                )
            )
        await self.motorista_repo.flush()

    async def _copy_itens_from_reserva(
        self, tenant_id: uuid.UUID, contrato_id: uuid.UUID, reserva_id: uuid.UUID
    ) -> None:
        stmt = select(ResReservaItem).where(
            ResReservaItem.reserva_id == reserva_id,
            ResReservaItem.deleted_at.is_(None),
        )
        for item in (await self.session.execute(stmt)).scalars().all():
            self.item_repo.add(
                _reserva_item_to_contrato_item(contrato_id, tenant_id, item)
            )
        await self.item_repo.flush()

    async def _copy_motoristas_from_reserva(
        self, tenant_id: uuid.UUID, contrato_id: uuid.UUID, reserva_id: uuid.UUID
    ) -> None:
        stmt = select(ResReservaMotorista).where(
            ResReservaMotorista.reserva_id == reserva_id,
            ResReservaMotorista.deleted_at.is_(None),
        )
        for mot in (await self.session.execute(stmt)).scalars().all():
            self.motorista_repo.add(
                LocContratoMotorista(
                    tenant_id=tenant_id,
                    contrato_id=contrato_id,
                    motorista_id=mot.motorista_id,
                    principal=mot.principal,
                )
            )
        await self.motorista_repo.flush()


class CheckoutService:
    """Processo de check-out / entrega do veículo (§6.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contrato_svc = ContratoService(session)
        self.contrato_repo = ContratoRepository(session)
        self.vistoria_repo = VistoriaRepository(session)
        self.foto_repo = VistoriaFotoRepository(session)
        self.veiculo_svc = VeiculoService(session)
        self.reserva_svc = ReservaService(session)

    async def iniciar(self, contrato_id: uuid.UUID) -> LocContrato:
        contrato = await self.contrato_svc.get(contrato_id)
        if contrato.status not in _CHECKOUT_ALLOWED:
            raise BusinessRuleError(
                "Contrato não está em status válido para check-out.",
                code="checkout_status_invalido",
            )
        if contrato.status == ContratoStatus.RASCUNHO:
            _assert_transition(contrato.status, ContratoStatus.AGUARDANDO_CHECKOUT)
            contrato.status = ContratoStatus.AGUARDANDO_CHECKOUT
            await self.contrato_repo.flush()
            await audit_service.record(
                AuditAction.UPDATE,
                entity="loc_contrato",
                entity_id=contrato.id,
                description=f"Check-out iniciado: {contrato.numero}",
            )
        return contrato

    async def concluir(
        self, contrato_id: uuid.UUID, data: CheckoutConcluirInput
    ) -> LocContrato:
        contrato = await self.contrato_svc.get(contrato_id)
        if contrato.status not in _CHECKOUT_ALLOWED:
            raise BusinessRuleError(
                "Contrato não está em status válido para concluir check-out.",
            )

        await self._validar_precondicoes(contrato, data)

        if not data.fotos:
            raise ValidationError("Check-out exige ao menos uma foto da vistoria.")

        now = data.realizado_em or datetime.now(tz=UTC)
        vistoria = LocVistoria(
            tenant_id=contrato.tenant_id,
            contrato_id=contrato.id,
            tipo=VistoriaTipo.CHECKOUT,
            km=data.km,
            combustivel_nivel=data.combustivel_nivel,
            observacoes=data.observacoes,
            realizado_em=now,
            realizado_por_user_id=data.realizado_por_user_id,
            checklist_json=json.dumps(data.checklist_json, ensure_ascii=False),
        )
        self.vistoria_repo.add(vistoria)
        await self.vistoria_repo.flush()

        for foto in data.fotos:
            self.foto_repo.add(
                LocVistoriaFoto(
                    tenant_id=contrato.tenant_id,
                    vistoria_id=vistoria.id,
                    storage_key=foto.storage_key,
                    angulo=foto.angulo,
                    ordem=foto.ordem,
                )
            )
        await self.foto_repo.flush()

        _assert_transition(contrato.status, ContratoStatus.ATIVO)
        contrato.status = ContratoStatus.ATIVO
        contrato.checkout_em = now
        contrato.km_saida = data.km
        contrato.combustivel_saida = data.combustivel_nivel
        if data.assinatura_tipo:
            contrato.assinatura_tipo = data.assinatura_tipo
        if data.assinatura_key:
            contrato.assinatura_key = data.assinatura_key

        await self.veiculo_svc.change_status(contrato.veiculo_id, VeiculoStatus.LOCADO)

        veiculo = await self.veiculo_svc.get(contrato.veiculo_id)
        veiculo.km_atual = data.km
        veiculo.nivel_combustivel_atual = data.combustivel_nivel

        if contrato.reserva_id:
            await self.reserva_svc.checkout_realizado(contrato.reserva_id)

        await self.contrato_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=f"Check-out concluído: {contrato.numero}",
        )
        return contrato

    async def _validar_precondicoes(
        self, contrato: LocContrato, data: CheckoutConcluirInput
    ) -> None:
        if not data.caucao_confirmada and not data.allow_force:
            raise BusinessRuleError(
                "Caução não confirmada.",
                code="caucao_nao_confirmada",
            )

        doc_stmt = select(FrotaDocumento).where(
            FrotaDocumento.veiculo_id == contrato.veiculo_id,
            FrotaDocumento.deleted_at.is_(None),
            FrotaDocumento.status == DocumentoVeiculoStatus.VENCIDO,
        )
        vencidos = list((await self.session.execute(doc_stmt)).scalars().all())
        if vencidos and not data.allow_force:
            raise BusinessRuleError(
                "Veículo possui documentação vencida.",
                code="documento_vencido",
            )

        mot_stmt = select(LocContratoMotorista).where(
            LocContratoMotorista.contrato_id == contrato.id,
            LocContratoMotorista.deleted_at.is_(None),
        )
        motoristas_vinc = list((await self.session.execute(mot_stmt)).scalars().all())
        if not motoristas_vinc and not data.allow_force:
            raise BusinessRuleError(
                "Contrato sem motorista autorizado.",
                code="sem_motorista",
            )

        for vinc in motoristas_vinc:
            mot = await self.session.get(Motorista, vinc.motorista_id)
            if mot is None or mot.deleted_at is not None:
                if not data.allow_force:
                    raise NotFoundError("Motorista do contrato não encontrado.")
                continue
            if mot.cnh_status in _CNH_INVALID and not data.allow_force:
                raise BusinessRuleError(
                    f"CNH do motorista {mot.nome} inválida ({mot.cnh_status.value}).",
                    code="cnh_invalida",
                )


class CheckinService:
    """Processo de check-in / devolução do veículo (§6.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contrato_svc = ContratoService(session)
        self.contrato_repo = ContratoRepository(session)
        self.vistoria_repo = VistoriaRepository(session)
        self.foto_repo = VistoriaFotoRepository(session)
        self.veiculo_svc = VeiculoService(session)
        self.avaria_svc = AvariaService(session)

    async def concluir(
        self, contrato_id: uuid.UUID, data: CheckinConcluirInput
    ) -> LocContrato:
        contrato = await self.contrato_svc.get(contrato_id)
        if contrato.status not in _CHECKIN_ALLOWED:
            raise BusinessRuleError(
                "Contrato não está em status válido para check-in.",
            )
        if contrato.km_saida is not None and data.km_entrada < contrato.km_saida:
            raise ValidationError("Km de entrada não pode ser menor que km de saída.")

        now = data.realizado_em or datetime.now(tz=UTC)
        vistoria = LocVistoria(
            tenant_id=contrato.tenant_id,
            contrato_id=contrato.id,
            tipo=VistoriaTipo.CHECKIN,
            km=data.km_entrada,
            combustivel_nivel=data.combustivel_entrada,
            observacoes=data.observacoes,
            realizado_em=now,
            realizado_por_user_id=data.realizado_por_user_id,
            checklist_json=json.dumps(data.checklist_json, ensure_ascii=False),
        )
        self.vistoria_repo.add(vistoria)
        await self.vistoria_repo.flush()

        for foto in data.fotos:
            self.foto_repo.add(
                LocVistoriaFoto(
                    tenant_id=contrato.tenant_id,
                    vistoria_id=vistoria.id,
                    storage_key=foto.storage_key,
                    angulo=foto.angulo,
                    ordem=foto.ordem,
                )
            )
        await self.foto_repo.flush()

        ajustes = await self._calcular_ajustes(contrato, data)
        contrato.ajustes_checkin = ajustes
        contrato.valor_final = _money(
            contrato.valor_total
            + ajustes
            - data.caucao_devolvida
            + data.caucao_retida
        )
        contrato.checkin_em = now
        contrato.km_entrada = data.km_entrada
        contrato.combustivel_entrada = data.combustivel_entrada
        contrato.pendencia_financeira = data.pendencia_financeira

        grave = False
        for av in data.avarias:
            avaria = await self.avaria_svc.create_from_checkin(
                contrato, vistoria.id, av
            )
            if avaria.severidade == AvariaSeveridade.GRAVE:
                grave = True

        if data.pendencia_financeira:
            novo_status = ContratoStatus.ENCERRADO_PENDENCIA
        else:
            novo_status = ContratoStatus.ENCERRADO
        _assert_transition(contrato.status, novo_status)
        contrato.status = novo_status

        veiculo = await self.veiculo_svc.get(contrato.veiculo_id)
        veiculo.km_atual = data.km_entrada
        veiculo.nivel_combustivel_atual = data.combustivel_entrada

        novo_veiculo_status = (
            VeiculoStatus.MANUTENCAO if grave else VeiculoStatus.DISPONIVEL
        )
        await self.veiculo_svc.change_status(contrato.veiculo_id, novo_veiculo_status)

        await self.contrato_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=(
                f"Check-in concluído: {contrato.numero} "
                f"(ajustes={ajustes}, final={contrato.valor_final})"
            ),
        )
        # Hook §7.5: credita pontos de fidelidade ao encerrar sem pendência.
        if novo_status == ContratoStatus.ENCERRADO:
            try:
                from app.modules.comercial.service import FidelidadeService

                await FidelidadeService(self.session).creditar_contrato(
                    contrato.tenant_id,
                    contrato_id=contrato.id,
                    cliente_id=contrato.cliente_id,
                    valor_total=contrato.valor_final or contrato.valor_total,
                    dias=contrato.dias,
                )
            except Exception:  # noqa: BLE001 - fidelidade não deve bloquear o check-in
                pass
            # Hook §10.1: emite NFS-e automaticamente quando configurado na filial.
            try:
                from app.modules.fiscal.service import ImpostoService, NfseService

                if await ImpostoService(self.session).nfse_automatica(
                    contrato.filial_retirada_id
                ):
                    nfse = await NfseService(self.session).create_from_contrato(
                        contrato.id, automatica=True
                    )
                    await NfseService(self.session).emitir(nfse.id)
            except Exception:  # noqa: BLE001 - fiscal não deve bloquear o check-in
                pass
            try:
                from app.modules.integracoes.outbound import notify_outbound_event

                await notify_outbound_event(
                    contrato.tenant_id,
                    "contrato.encerrado",
                    {
                        "id": str(contrato.id),
                        "numero": contrato.numero,
                        "status": contrato.status.value,
                        "valor_final": str(contrato.valor_final or contrato.valor_total),
                    },
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                from app.modules.automacoes.hooks import fire_regra_event
                from app.shared.enums import AutoEventoGatilho

                await fire_regra_event(
                    self.session,
                    contrato.tenant_id,
                    AutoEventoGatilho.CONTRATO_ENCERRADO,
                    {
                        "contrato_id": str(contrato.id),
                        "numero": contrato.numero,
                        "cliente_id": str(contrato.cliente_id),
                        "veiculo_id": str(contrato.veiculo_id),
                        "valor_final": float(contrato.valor_final or contrato.valor_total),
                    },
                )
            except Exception:  # noqa: BLE001
                pass
        return contrato

    async def _calcular_ajustes(
        self, contrato: LocContrato, data: CheckinConcluirInput
    ) -> Decimal:
        total = _ZERO

        if (
            contrato.combustivel_saida is not None
            and data.combustivel_entrada < contrato.combustivel_saida
        ):
            octavos_faltantes = contrato.combustivel_saida - data.combustivel_entrada
            preco_litro, capacidade = await self._fuel_params(contrato.veiculo_id)
            litros = (Decimal(octavos_faltantes) / Decimal(8)) * capacidade
            total += _money(litros * preco_litro)

        if data.horas_atraso > 0:
            hora_extra = _money(contrato.diaria_unitaria / Decimal(24))
            total += _money(data.horas_atraso * hora_extra)

        total += _money(data.valor_km_excedente)
        for av in data.avarias:
            if av.valor_reparo:
                total += _money(av.valor_reparo)

        return _money(total)

    async def _fuel_params(self, veiculo_id: uuid.UUID) -> tuple[Decimal, Decimal]:
        veiculo = await self.veiculo_svc.get(veiculo_id)
        comb = await self.session.get(FrotaCombustivel, veiculo.combustivel_id)
        preco = comb.preco_referencia if comb else _ZERO
        modelo = await self.session.get(FrotaModelo, veiculo.modelo_id)
        capacidade = (
            modelo.capacidade_tanque
            if modelo and modelo.capacidade_tanque
            else _DEFAULT_TANK_LITERS
        )
        return preco, capacidade


class RenovacaoService:
    """Renovações e aditivos contratuais (§6.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contrato_svc = ContratoService(session)
        self.contrato_repo = ContratoRepository(session)
        self.aditivo_repo = ContratoAditivoRepository(session)
        self.pricing = PricingService(session)
        self.disponibilidade = DisponibilidadeService(session)

    async def renovar(
        self, contrato_id: uuid.UUID, data: RenovacaoInput
    ) -> LocContrato:
        contrato = await self.contrato_svc.get(contrato_id)
        if contrato.status != ContratoStatus.ATIVO:
            raise BusinessRuleError("Somente contratos ativos podem ser renovados.")

        if data.nova_devolucao <= contrato.devolucao_prevista_em:
            raise ValidationError(
                "Nova devolução deve ser posterior à devolução prevista atual."
            )

        conflitos = await self.contrato_repo.overlapping_for_period(
            inicio=contrato.devolucao_prevista_em,
            fim=data.nova_devolucao,
            veiculo_id=contrato.veiculo_id,
            statuses=_BLOCKING_CONTRATO_STATUSES,
            exclude_contrato_id=contrato.id,
        )
        if conflitos:
            raise ConflictError(
                "Veículo indisponível para o período de renovação.",
                code="conflito_renovacao",
            )

        disp = await self.disponibilidade.consultar(
            contrato.filial_retirada_id,
            contrato.devolucao_prevista_em,
            data.nova_devolucao,
            categoria_id=contrato.categoria_id,
        )
        for cat in disp:
            for v in cat.veiculos:
                if v.id == contrato.veiculo_id and not v.disponivel:
                    raise ConflictError(
                        "Veículo possui conflito de reserva no período extra.",
                        code="conflito_reserva",
                    )

        quote = await self.pricing.calcular(
            PricingQuoteInput(
                tenant_id=contrato.tenant_id,
                filial_id=contrato.filial_retirada_id,
                categoria_id=contrato.categoria_id,
                canal=TarifarioCanal.BALCAO,
                retirada_em=contrato.devolucao_prevista_em,
                devolucao_em=data.nova_devolucao,
                veiculo_id=contrato.veiculo_id,
                cliente_id=contrato.cliente_id,
            )
        )
        dias_extra = quote.dias
        valor_aditivo = _money(quote.total)

        devolucao_anterior = contrato.devolucao_prevista_em
        contrato.devolucao_prevista_em = data.nova_devolucao
        contrato.versao += 1
        contrato.dias += dias_extra
        contrato.valor_total = _money(contrato.valor_total + valor_aditivo)

        aditivo = LocContratoAditivo(
            tenant_id=contrato.tenant_id,
            contrato_id=contrato.id,
            versao=contrato.versao,
            devolucao_anterior=devolucao_anterior,
            devolucao_nova=data.nova_devolucao,
            dias_extra=dias_extra,
            valor_aditivo=valor_aditivo,
            pricing_snapshot=json.dumps(quote.snapshot, ensure_ascii=False),
            aprovado=data.aprovado,
            motivo=data.motivo,
        )
        self.aditivo_repo.add(aditivo)
        await self.aditivo_repo.flush()
        await self.contrato_repo.flush()

        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=(
                f"Renovação v{contrato.versao}: {contrato.numero} "
                f"(+{dias_extra}d, +{valor_aditivo})"
            ),
        )
        return contrato


class EncerramentoService:
    """Gestão de contratos encerrados e pendências (§6.5)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.contrato_svc = ContratoService(session)
        self.contrato_repo = ContratoRepository(session)

    async def list_encerrados(
        self,
        params: PageParams,
        *,
        pendencia_financeira: bool | None = None,
        cliente_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Page[LocContrato]:
        statuses = {
            ContratoStatus.ENCERRADO,
            ContratoStatus.ENCERRADO_PENDENCIA,
        }
        return await self.contrato_svc.list_items(
            params,
            statuses=statuses,
            pendencia_financeira=pendencia_financeira,
            cliente_id=cliente_id,
            search=search,
        )

    async def list_pendencias(
        self, params: PageParams, *, cliente_id: uuid.UUID | None = None
    ) -> Page[LocContrato]:
        return await self.contrato_svc.list_items(
            params,
            status=ContratoStatus.ENCERRADO_PENDENCIA,
            pendencia_financeira=True,
            cliente_id=cliente_id,
        )

    async def reabrir(
        self, contrato_id: uuid.UUID, data: ReabrirInput
    ) -> LocContrato:
        contrato = await self.contrato_svc.get(contrato_id)
        if contrato.status not in {
            ContratoStatus.ENCERRADO,
            ContratoStatus.ENCERRADO_PENDENCIA,
        }:
            raise BusinessRuleError(
                "Somente contratos encerrados podem ser reabertos.",
            )

        _assert_transition(contrato.status, ContratoStatus.AGUARDANDO_CHECKIN)
        contrato.status = ContratoStatus.AGUARDANDO_CHECKIN
        contrato.checkin_em = None
        contrato.valor_final = None
        contrato.ajustes_checkin = _ZERO
        contrato.pendencia_financeira = False

        await self.contrato_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_contrato",
            entity_id=contrato.id,
            description=f"Contrato reaberto: {contrato.numero} — {data.motivo}",
        )
        return contrato


class MultaService:
    """Gestão de multas de trânsito (§6.6)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MultaRepository(session)
        self.contrato_repo = ContratoRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        veiculo_id: uuid.UUID | None = None,
        contrato_id: uuid.UUID | None = None,
        cliente_id: uuid.UUID | None = None,
        status: MultaStatus | None = None,
    ) -> Page[LocMulta]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(
                veiculo_id=veiculo_id,
                contrato_id=contrato_id,
                cliente_id=cliente_id,
                status=status,
            ),
        )

    async def get(self, multa_id: uuid.UUID) -> LocMulta:
        item = await self.repo.get(multa_id)
        if item is None:
            raise NotFoundError("Multa não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: MultaCreate) -> LocMulta:
        multa = LocMulta(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(multa)
        await self.repo.flush()
        await self.vincular_auto(multa.id)
        await audit_service.record(
            AuditAction.CREATE,
            entity="loc_multa",
            entity_id=multa.id,
            description=f"Multa registrada: veículo {data.veiculo_id}",
        )
        return await self.get(multa.id)

    async def update(self, multa_id: uuid.UUID, data: MultaUpdate) -> LocMulta:
        multa = await self.get(multa_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(multa, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_multa",
            entity_id=multa.id,
            description="Multa atualizada",
        )
        return multa

    async def delete(self, multa_id: uuid.UUID) -> None:
        multa = await self.get(multa_id)
        await self.repo.delete(multa)
        await audit_service.record(
            AuditAction.DELETE,
            entity="loc_multa",
            entity_id=multa.id,
            description="Multa excluída",
        )

    async def vincular_auto(self, multa_id: uuid.UUID) -> LocMulta:
        multa = await self.get(multa_id)
        if multa.contrato_id:
            return multa

        candidatos = await self.contrato_repo.active_at_moment(
            veiculo_id=multa.veiculo_id,
            momento=multa.ocorrido_em,
        )
        if not candidatos:
            stmt = self.contrato_repo.list_query(veiculo_id=multa.veiculo_id)
            stmt = stmt.where(
                LocContrato.retirada_prevista_em <= multa.ocorrido_em,
                LocContrato.devolucao_prevista_em >= multa.ocorrido_em,
                LocContrato.status.in_(
                    {
                        ContratoStatus.ATIVO,
                        ContratoStatus.AGUARDANDO_CHECKIN,
                        ContratoStatus.ENCERRADO,
                        ContratoStatus.ENCERRADO_PENDENCIA,
                    }
                ),
            )
            candidatos = list((await self.session.execute(stmt)).scalars().all())

        if len(candidatos) == 1:
            contrato = candidatos[0]
            multa.contrato_id = contrato.id
            multa.cliente_id = contrato.cliente_id
            multa.status = MultaStatus.VINCULADA
            await self.repo.flush()
        return multa

    async def marcar_notificado(self, multa_id: uuid.UUID) -> LocMulta:
        multa = await self.get(multa_id)
        multa.status = MultaStatus.NOTIFICADO
        await self.repo.flush()
        await self.gerar_cobranca(multa_id)
        return multa

    async def gerar_cobranca(self, multa_id: uuid.UUID) -> LocMulta:
        """Gera título a receber para a multa vinculada a cliente/contrato (§9.2)."""
        multa = await self.get(multa_id)
        if not multa.contrato_id or not multa.cliente_id:
            return multa
        contrato = await self.contrato_repo.get(multa.contrato_id)
        if contrato is None:
            return multa
        from app.modules.financeiro.models import FinContaReceber
        from app.modules.financeiro.service import ContaReceberService
        from app.shared.enums import ContaReceberOrigem

        cr_svc = ContaReceberService(self.session)
        dup_stmt = (
            cr_svc.repo._base_query()
            .where(
                FinContaReceber.origem == ContaReceberOrigem.MULTA,
                FinContaReceber.origem_id == multa.id,
            )
            .limit(1)
        )
        if (await self.session.execute(dup_stmt)).scalar_one_or_none() is not None:
            return multa
        valor = multa.valor + (multa.taxa_admin or Decimal("0"))
        await cr_svc.from_origem(
            multa.tenant_id,
            origem=ContaReceberOrigem.MULTA,
            origem_id=multa.id,
            cliente_id=multa.cliente_id,
            filial_id=contrato.filial_retirada_id,
            valor=valor,
            descricao=f"Multa {multa.codigo_infracao} ({multa.orgao})",
        )
        return multa

    async def marcar_paga(self, multa_id: uuid.UUID) -> LocMulta:
        multa = await self.get(multa_id)
        multa.status = MultaStatus.PAGA
        await self.repo.flush()
        return multa


class AvariaService:
    """Gestão do ciclo de vida de avarias (§6.7)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AvariaRepository(session)
        self.foto_repo = AvariaFotoRepository(session)
        self.os_svc = OrdemServicoService(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        veiculo_id: uuid.UUID | None = None,
        contrato_id: uuid.UUID | None = None,
        status: AvariaStatus | None = None,
    ) -> Page[LocAvaria]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(
                veiculo_id=veiculo_id,
                contrato_id=contrato_id,
                status=status,
            ),
        )

    async def get(self, avaria_id: uuid.UUID) -> LocAvaria:
        item = await self.repo.get(avaria_id)
        if item is None:
            raise NotFoundError("Avaria não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: AvariaCreate) -> LocAvaria:
        avaria = LocAvaria(
            tenant_id=tenant_id,
            veiculo_id=data.veiculo_id,
            contrato_id=data.contrato_id,
            vistoria_id=data.vistoria_id,
            origem=data.origem,
            localizacao=data.localizacao,
            severidade=data.severidade,
            laudo=data.laudo,
            valor_reparo=data.valor_reparo,
            observacoes=data.observacoes,
            status=AvariaStatus.REGISTRADA,
        )
        self.repo.add(avaria)
        await self.repo.flush()
        await self._sync_fotos(tenant_id, avaria.id, data.fotos)
        await audit_service.record(
            AuditAction.CREATE,
            entity="loc_avaria",
            entity_id=avaria.id,
            description=f"Avaria registrada: {data.localizacao}",
        )
        return avaria

    async def create_from_checkin(
        self,
        contrato: LocContrato,
        vistoria_id: uuid.UUID,
        data: AvariaCheckinInput,
    ) -> LocAvaria:
        return await self.create(
            contrato.tenant_id,
            AvariaCreate(
                veiculo_id=contrato.veiculo_id,
                contrato_id=contrato.id,
                vistoria_id=vistoria_id,
                origem=AvariaOrigem.CHECKIN,
                localizacao=data.localizacao,
                severidade=data.severidade,
                laudo=data.laudo,
                valor_reparo=data.valor_reparo,
                fotos=data.fotos,
                observacoes=data.observacoes,
            ),
        )

    async def update(self, avaria_id: uuid.UUID, data: AvariaUpdate) -> LocAvaria:
        avaria = await self.get(avaria_id)
        if avaria.status == AvariaStatus.ENCERRADA:
            raise BusinessRuleError("Avaria encerrada não pode ser alterada.")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(avaria, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_avaria",
            entity_id=avaria.id,
            description="Avaria atualizada",
        )
        return avaria

    async def definir_responsabilidade(
        self, avaria_id: uuid.UUID, data: AvariaResponsabilidadeInput
    ) -> LocAvaria:
        avaria = await self.get(avaria_id)
        avaria.responsabilidade = data.responsabilidade
        avaria.status = AvariaStatus.RESPONSABILIDADE_DEFINIDA
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_avaria",
            entity_id=avaria.id,
            description=f"Responsabilidade definida: {data.responsabilidade.value}",
        )
        if (
            data.responsabilidade == AvariaResponsabilidade.CLIENTE
            and avaria.contrato_id
            and avaria.valor_reparo
            and avaria.valor_reparo > 0
        ):
            await self._gerar_cobranca_cliente(avaria)
        return avaria

    async def _gerar_cobranca_cliente(self, avaria: LocAvaria) -> None:
        """Gera um título a receber para a avaria de responsabilidade do cliente (§9.2)."""
        contrato = await ContratoRepository(self.session).get(avaria.contrato_id)
        if contrato is None:
            return
        from app.modules.financeiro.service import ContaReceberService
        from app.shared.enums import ContaReceberOrigem

        await ContaReceberService(self.session).from_origem(
            avaria.tenant_id,
            origem=ContaReceberOrigem.AVARIA,
            origem_id=avaria.id,
            cliente_id=contrato.cliente_id,
            filial_id=contrato.filial_retirada_id,
            valor=avaria.valor_reparo,
            descricao=f"Avaria {avaria.localizacao} (contrato {contrato.numero})",
        )

    async def gerar_os(self, avaria_id: uuid.UUID) -> LocAvaria:
        avaria = await self.get(avaria_id)
        if avaria.severidade != AvariaSeveridade.GRAVE:
            raise BusinessRuleError(
                "OS corretiva só é gerada automaticamente para avarias graves.",
            )
        if avaria.os_id:
            raise ConflictError("Avaria já possui OS vinculada.", code="os_existente")

        os = await self.os_svc.create(
            avaria.tenant_id,
            OrdemServicoCreate(
                veiculo_id=avaria.veiculo_id,
                tipo=OrdemServicoTipo.CORRETIVA,
                origem=OrdemServicoOrigem.AVARIA_CHECKIN,
                km_entrada=None,
                causa=CorretivaCausa.ACIDENTE,
                responsavel_custo=(
                    CorretivaResponsavel.CLIENTE
                    if avaria.responsabilidade == AvariaResponsabilidade.CLIENTE
                    else CorretivaResponsavel.LOCADORA
                ),
                observacoes=avaria.laudo or f"Avaria {avaria.localizacao}",
            ),
        )
        avaria.os_id = os.id
        avaria.status = AvariaStatus.OS_GERADA
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="loc_avaria",
            entity_id=avaria.id,
            description=f"OS gerada: {os.numero}",
        )
        return avaria

    async def encerrar(self, avaria_id: uuid.UUID) -> LocAvaria:
        avaria = await self.get(avaria_id)
        avaria.status = AvariaStatus.ENCERRADA
        await self.repo.flush()
        return avaria

    async def _sync_fotos(
        self, tenant_id: uuid.UUID, avaria_id: uuid.UUID, keys: list[str]
    ) -> None:
        for key in keys:
            self.foto_repo.add(
                LocAvariaFoto(
                    tenant_id=tenant_id,
                    avaria_id=avaria_id,
                    storage_key=key,
                )
            )
        if keys:
            await self.foto_repo.flush()
