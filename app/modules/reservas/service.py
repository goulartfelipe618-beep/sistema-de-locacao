"""Serviços de negócio do módulo Reservas (§5.1–5.5)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.cadastros.models import Cliente
from app.modules.frota.models import FrotaCategoria, FrotaVeiculo
from app.modules.frota.service import VeiculoService
from app.modules.reservas.models import (
    ResCotacao,
    ResReserva,
    ResReservaItem,
    ResReservaMotorista,
)
from app.modules.reservas.schemas import (
    CalendarioEvento,
    CotacaoConverterInput,
    CotacaoCreate,
    CotacaoUpdate,
    DisponibilidadeCategoria,
    DisponibilidadeVeiculo,
    ReservaCancelInput,
    ReservaCreate,
    ReservaUpdate,
)
from app.modules.tarifario.schemas import PricingLineItem, PricingQuoteInput
from app.modules.tarifario.service import PricingService
from app.shared.enums import (
    AuditAction,
    ClienteStatus,
    CotacaoStatus,
    ReservaAlocacao,
    ReservaItemTipo,
    ReservaOrigem,
    ReservaStatus,
    TarifarioCanal,
    VeiculoStatus,
)
from app.shared.repository import BaseRepository

_MONEY = Decimal("0.01")
_ZERO = Decimal("0")

_CAPACITY_STATUSES = {
    VeiculoStatus.DISPONIVEL,
    VeiculoStatus.RESERVADO,
    VeiculoStatus.LOCADO,
}
_EXCLUDED_STATUSES = {
    VeiculoStatus.MANUTENCAO,
    VeiculoStatus.BLOQUEADO,
    VeiculoStatus.BAIXADO,
    VeiculoStatus.RESTRITO,
}
_BLOCKING_RESERVA_STATUSES = {ReservaStatus.CONFIRMADA}
_EDITABLE_RESERVA_STATUSES = {ReservaStatus.PENDENTE}

RESERVA_TRANSITIONS: dict[ReservaStatus, set[ReservaStatus]] = {
    ReservaStatus.PENDENTE: {
        ReservaStatus.CONFIRMADA,
        ReservaStatus.CANCELADA,
    },
    ReservaStatus.CONFIRMADA: {
        ReservaStatus.CHECKOUT,
        ReservaStatus.CANCELADA,
        ReservaStatus.NO_SHOW,
    },
    ReservaStatus.CHECKOUT: {ReservaStatus.CONCLUIDA},
    ReservaStatus.CONCLUIDA: set(),
    ReservaStatus.CANCELADA: set(),
    ReservaStatus.NO_SHOW: set(),
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
class ReservaRepository(BaseRepository[ResReserva]):
    model = ResReserva

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ResReserva)
            .where(
                ResReserva.tenant_id == tenant_id,
                ResReserva.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: ReservaStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        veiculo_id: uuid.UUID | None = None,
        filial_id: uuid.UUID | None = None,
        retirada_de: datetime | None = None,
        retirada_ate: datetime | None = None,
        search: str | None = None,
    ) -> Select[tuple[ResReserva]]:
        stmt = self._base_query().order_by(ResReserva.retirada_em.desc())
        if status:
            stmt = stmt.where(ResReserva.status == status)
        if cliente_id:
            stmt = stmt.where(ResReserva.cliente_id == cliente_id)
        if veiculo_id:
            stmt = stmt.where(ResReserva.veiculo_id == veiculo_id)
        if filial_id:
            stmt = stmt.where(
                or_(
                    ResReserva.filial_retirada_id == filial_id,
                    ResReserva.filial_devolucao_id == filial_id,
                )
            )
        if retirada_de:
            stmt = stmt.where(ResReserva.retirada_em >= retirada_de)
        if retirada_ate:
            stmt = stmt.where(ResReserva.retirada_em <= retirada_ate)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(ResReserva.numero).like(term))
        return stmt

    async def overlapping_for_period(
        self,
        *,
        inicio: datetime,
        fim: datetime,
        statuses: set[ReservaStatus],
        filial_id: uuid.UUID | None = None,
        categoria_id: uuid.UUID | None = None,
        veiculo_id: uuid.UUID | None = None,
        exclude_reserva_id: uuid.UUID | None = None,
    ) -> list[ResReserva]:
        stmt = self._base_query().where(
            ResReserva.status.in_(statuses),
            ResReserva.retirada_em < fim,
            ResReserva.devolucao_em > inicio,
        )
        if filial_id:
            stmt = stmt.where(ResReserva.filial_retirada_id == filial_id)
        if categoria_id:
            stmt = stmt.where(ResReserva.categoria_id == categoria_id)
        if veiculo_id:
            stmt = stmt.where(ResReserva.veiculo_id == veiculo_id)
        if exclude_reserva_id:
            stmt = stmt.where(ResReserva.id != exclude_reserva_id)
        return list((await self.session.execute(stmt)).scalars().all())


class ReservaItemRepository(BaseRepository[ResReservaItem]):
    model = ResReservaItem

    async def delete_by_reserva(self, reserva_id: uuid.UUID) -> None:
        stmt = select(ResReservaItem).where(
            ResReservaItem.reserva_id == reserva_id,
            ResReservaItem.deleted_at.is_(None),
        )
        for row in (await self.session.execute(stmt)).scalars().all():
            await self.delete(row)


class ReservaMotoristaRepository(BaseRepository[ResReservaMotorista]):
    model = ResReservaMotorista

    async def delete_by_reserva(self, reserva_id: uuid.UUID) -> None:
        stmt = select(ResReservaMotorista).where(
            ResReservaMotorista.reserva_id == reserva_id,
            ResReservaMotorista.deleted_at.is_(None),
        )
        for row in (await self.session.execute(stmt)).scalars().all():
            await self.delete(row)

    def list_by_reserva(self, reserva_id: uuid.UUID) -> Select[tuple[ResReservaMotorista]]:
        return self._base_query().where(ResReservaMotorista.reserva_id == reserva_id)


class CotacaoRepository(BaseRepository[ResCotacao]):
    model = ResCotacao

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ResCotacao)
            .where(
                ResCotacao.tenant_id == tenant_id,
                ResCotacao.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: CotacaoStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Select[tuple[ResCotacao]]:
        stmt = self._base_query().order_by(ResCotacao.created_at.desc())
        if status:
            stmt = stmt.where(ResCotacao.status == status)
        if cliente_id:
            stmt = stmt.where(ResCotacao.cliente_id == cliente_id)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(ResCotacao.numero).like(term))
        return stmt


# --------------------------------------------------------------------- Helpers
def _money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY)


def _origem_canal(origem: ReservaOrigem) -> TarifarioCanal:
    return _ORIGEM_CANAL.get(origem, TarifarioCanal.BALCAO)


def _apply_buffer(inicio: datetime, fim: datetime, buffer_horas: int) -> tuple[datetime, datetime]:
    delta = timedelta(hours=buffer_horas)
    return inicio - delta, fim + delta


def _line_to_item(reserva_id: uuid.UUID, tenant_id: uuid.UUID, line: PricingLineItem) -> ResReservaItem:
    tipo = _ITEM_TIPO_MAP.get(line.tipo, ReservaItemTipo.TAXA)
    return ResReservaItem(
        tenant_id=tenant_id,
        reserva_id=reserva_id,
        tipo=tipo,
        referencia_id=line.referencia_id,
        descricao=line.nome,
        quantidade=line.quantidade,
        valor_unitario=line.valor_unitario,
        valor_total=line.valor_total,
    )


def _pricing_to_reserva_fields(pricing, *, desconto: Decimal = _ZERO) -> dict:
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
        "valor_total": valor_total,
        "pricing_snapshot": json.dumps(pricing.snapshot, ensure_ascii=False),
    }


# --------------------------------------------------------------------- Services
class DisponibilidadeService:
    """Motor de consulta de disponibilidade (§5.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reserva_repo = ReservaRepository(session)

    async def consultar(
        self,
        filial_id: uuid.UUID,
        inicio: datetime,
        fim: datetime,
        *,
        categoria_id: uuid.UUID | None = None,
        buffer_horas: int = 2,
        overbooking_pct: int = 0,
    ) -> list[DisponibilidadeCategoria]:
        if fim <= inicio:
            raise ValidationError("Período inválido: fim deve ser posterior ao início.")

        inicio_buf, fim_buf = _apply_buffer(inicio, fim, buffer_horas)

        veiculo_stmt = select(FrotaVeiculo).where(
            FrotaVeiculo.deleted_at.is_(None),
            FrotaVeiculo.filial_id == filial_id,
            FrotaVeiculo.status.in_(_CAPACITY_STATUSES),
        )
        if categoria_id:
            veiculo_stmt = veiculo_stmt.where(FrotaVeiculo.categoria_id == categoria_id)
        veiculos = list((await self.session.execute(veiculo_stmt)).scalars().all())

        cat_ids = {v.categoria_id for v in veiculos}
        if not cat_ids:
            return []

        cat_stmt = select(FrotaCategoria).where(
            FrotaCategoria.id.in_(cat_ids),
            FrotaCategoria.deleted_at.is_(None),
        )
        categorias = {
            c.id: c for c in (await self.session.execute(cat_stmt)).scalars().all()
        }

        overlapping = await self.reserva_repo.overlapping_for_period(
            inicio=inicio_buf,
            fim=fim_buf,
            statuses=_BLOCKING_RESERVA_STATUSES,
            filial_id=filial_id,
            categoria_id=categoria_id,
        )

        blocked_vehicle_ids: set[uuid.UUID] = {
            r.veiculo_id for r in overlapping if r.veiculo_id is not None
        }
        ocupados_por_categoria: dict[uuid.UUID, int] = {}
        for reserva in overlapping:
            if reserva.veiculo_id is None:
                ocupados_por_categoria[reserva.categoria_id] = (
                    ocupados_por_categoria.get(reserva.categoria_id, 0) + 1
                )

        por_categoria: dict[uuid.UUID, list[FrotaVeiculo]] = {}
        for veiculo in veiculos:
            por_categoria.setdefault(veiculo.categoria_id, []).append(veiculo)

        resultado: list[DisponibilidadeCategoria] = []
        for cat_id, lista in por_categoria.items():
            categoria = categorias.get(cat_id)
            if categoria is None:
                continue

            veiculo_rows: list[DisponibilidadeVeiculo] = []
            livres_veiculos = 0
            for v in lista:
                disponivel = (
                    v.status == VeiculoStatus.DISPONIVEL
                    and v.status not in _EXCLUDED_STATUSES
                    and v.id not in blocked_vehicle_ids
                )
                if disponivel:
                    livres_veiculos += 1
                veiculo_rows.append(
                    DisponibilidadeVeiculo(id=v.id, placa=v.placa, disponivel=disponivel)
                )

            total_frota = len(lista)
            ocupados_reservas = ocupados_por_categoria.get(cat_id, 0)
            ocupados_veiculos = sum(
                1
                for v in lista
                if v.id in blocked_vehicle_ids
                or v.status in {VeiculoStatus.RESERVADO, VeiculoStatus.LOCADO}
            )
            ocupados = max(ocupados_reservas + len(blocked_vehicle_ids), ocupados_veiculos)
            capacidade_efetiva = int(total_frota * (1 + overbooking_pct / 100))
            livres = max(0, capacidade_efetiva - ocupados)
            livres = min(livres, livres_veiculos + max(0, capacidade_efetiva - total_frota))

            resultado.append(
                DisponibilidadeCategoria(
                    categoria_id=cat_id,
                    nome=categoria.nome,
                    total_frota=total_frota,
                    ocupados=ocupados,
                    livres=livres,
                    veiculos=sorted(veiculo_rows, key=lambda x: x.placa),
                )
            )

        return sorted(resultado, key=lambda x: x.nome)


class ReservaService:
    """Gestão de reservas e workflow (§5.1–5.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReservaRepository(session)
        self.item_repo = ReservaItemRepository(session)
        self.motorista_repo = ReservaMotoristaRepository(session)
        self.pricing = PricingService(session)
        self.veiculo_svc = VeiculoService(session)
        self.disponibilidade = DisponibilidadeService(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"RES-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: ReservaStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        veiculo_id: uuid.UUID | None = None,
        filial_id: uuid.UUID | None = None,
        retirada_de: datetime | None = None,
        retirada_ate: datetime | None = None,
        search: str | None = None,
    ) -> Page[ResReserva]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(
                status=status,
                cliente_id=cliente_id,
                veiculo_id=veiculo_id,
                filial_id=filial_id,
                retirada_de=retirada_de,
                retirada_ate=retirada_ate,
                search=search,
            ),
        )

    async def get(self, reserva_id: uuid.UUID) -> ResReserva:
        item = await self.repo.get(reserva_id)
        if item is None:
            raise NotFoundError("Reserva não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: ReservaCreate) -> ResReserva:
        cliente = await self._get_cliente(data.cliente_id)
        requer_aprovacao = cliente.status == ClienteStatus.BLOCKED

        alocacao = (
            ReservaAlocacao.VEICULO if data.veiculo_id else ReservaAlocacao.CATEGORIA
        )
        if data.veiculo_id:
            await self._assert_veiculo_disponivel(
                data.veiculo_id,
                data.filial_retirada_id,
                data.categoria_id,
                data.retirada_em,
                data.devolucao_em,
            )

        pricing_input = self._build_pricing_input(tenant_id, data)
        quote = await self.pricing.calcular(pricing_input)

        # Hook §7.4: valida e aplica cupom de desconto, se informado.
        desconto_efetivo = data.desconto
        cupom_result = None
        if data.cupom_codigo:
            from app.modules.comercial.schemas import CupomValidarInput
            from app.modules.comercial.service import CupomService

            cupom_result = await CupomService(self.session).validar(
                CupomValidarInput(
                    codigo=data.cupom_codigo,
                    cliente_id=data.cliente_id,
                    categoria_id=data.categoria_id,
                    valor_base=quote.total,
                )
            )
            if not cupom_result.ok:
                raise BusinessRuleError(cupom_result.motivo or "Cupom inválido.")
            if cupom_result.desconto > desconto_efetivo:
                desconto_efetivo = cupom_result.desconto

        politica_id = data.politica_cancelamento_id or quote.politica_sugerida_id
        politica_snapshot = None
        if politica_id:
            from app.modules.tarifario.models import TarPoliticaCancelamento

            pol = await self.session.get(TarPoliticaCancelamento, politica_id)
            if pol:
                politica_snapshot = json.dumps(
                    {"id": str(pol.id), "nome": pol.nome, "descricao": pol.descricao},
                    ensure_ascii=False,
                )

        numero = await self.next_numero(tenant_id)
        fields = _pricing_to_reserva_fields(quote, desconto=desconto_efetivo)
        reserva = ResReserva(
            tenant_id=tenant_id,
            numero=numero,
            status=ReservaStatus.PENDENTE,
            alocacao=alocacao,
            origem=data.origem,
            cliente_id=data.cliente_id,
            categoria_id=data.categoria_id,
            veiculo_id=data.veiculo_id,
            filial_retirada_id=data.filial_retirada_id,
            filial_devolucao_id=data.filial_devolucao_id,
            retirada_em=data.retirada_em,
            devolucao_em=data.devolucao_em,
            endereco_entrega=data.endereco_entrega,
            vendedor_id=data.vendedor_id,
            parceiro_id=data.parceiro_id,
            politica_cancelamento_id=politica_id,
            forma_pagamento_prevista=data.forma_pagamento_prevista,
            cupom_codigo=data.cupom_codigo,
            observacoes=data.observacoes,
            politica_snapshot=politica_snapshot,
            requer_aprovacao=requer_aprovacao,
            **fields,
        )
        self.repo.add(reserva)
        await self.repo.flush()

        await self._sync_itens(tenant_id, reserva.id, quote)
        await self._sync_motoristas(tenant_id, reserva.id, data.motoristas)

        # Hook §7.4: registra o uso do cupom validado na reserva recém-criada.
        if cupom_result is not None and cupom_result.ok and cupom_result.cupom_id:
            from app.modules.comercial.service import CupomService

            await CupomService(self.session).aplicar(
                cupom_result.cupom_id,
                cliente_id=data.cliente_id,
                reserva_id=reserva.id,
                desconto_aplicado=cupom_result.desconto,
            )

        await audit_service.record(
            AuditAction.CREATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"Reserva criada: {reserva.numero}",
        )
        return reserva

    async def update(self, reserva_id: uuid.UUID, data: ReservaUpdate) -> ResReserva:
        reserva = await self.get(reserva_id)
        if reserva.status not in _EDITABLE_RESERVA_STATUSES:
            raise BusinessRuleError("Somente reservas pendentes podem ser editadas.")

        payload = data.model_dump(exclude_unset=True)
        motoristas = payload.pop("motoristas", None)
        protecao_ids = payload.pop("protecao_ids", None)
        taxa_ids = payload.pop("taxa_ids", None)
        acessorio_ids = payload.pop("acessorio_ids", None)
        desconto = payload.pop("desconto", None)

        for key, value in payload.items():
            setattr(reserva, key, value)

        if any(
            k in data.model_dump(exclude_unset=True)
            for k in (
                "retirada_em",
                "devolucao_em",
                "categoria_id",
                "filial_retirada_id",
                "filial_devolucao_id",
                "veiculo_id",
            )
        ) or protecao_ids is not None or taxa_ids is not None or acessorio_ids is not None:
            create_like = ReservaCreate(
                cliente_id=reserva.cliente_id,
                categoria_id=reserva.categoria_id,
                filial_retirada_id=reserva.filial_retirada_id,
                filial_devolucao_id=reserva.filial_devolucao_id,
                retirada_em=reserva.retirada_em,
                devolucao_em=reserva.devolucao_em,
                origem=reserva.origem,
                veiculo_id=reserva.veiculo_id,
                parceiro_id=reserva.parceiro_id,
                protecao_ids=protecao_ids or [],
                taxa_ids=taxa_ids or [],
                acessorio_ids=acessorio_ids or [],
                desconto=desconto if desconto is not None else reserva.desconto,
            )
            quote = await self.pricing.calcular(
                self._build_pricing_input(reserva.tenant_id, create_like)
            )
            fields = _pricing_to_reserva_fields(
                quote, desconto=desconto if desconto is not None else reserva.desconto
            )
            for key, value in fields.items():
                setattr(reserva, key, value)
            await self.item_repo.delete_by_reserva(reserva.id)
            await self._sync_itens(reserva.tenant_id, reserva.id, quote)

        if motoristas is not None:
            await self.motorista_repo.delete_by_reserva(reserva.id)
            await self._sync_motoristas(reserva.tenant_id, reserva.id, motoristas)

        if reserva.veiculo_id:
            reserva.alocacao = ReservaAlocacao.VEICULO
        else:
            reserva.alocacao = ReservaAlocacao.CATEGORIA

        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"Reserva atualizada: {reserva.numero}",
        )
        return reserva

    async def confirmar(self, reserva_id: uuid.UUID) -> ResReserva:
        reserva = await self.get(reserva_id)
        if reserva.status != ReservaStatus.PENDENTE:
            raise BusinessRuleError("Somente reservas pendentes podem ser confirmadas.")
        if reserva.requer_aprovacao:
            raise BusinessRuleError(
                "Reserva de cliente bloqueado requer aprovação manual.",
                code="requer_aprovacao",
            )

        if reserva.alocacao == ReservaAlocacao.VEICULO and reserva.veiculo_id:
            conflitos = await self.repo.overlapping_for_period(
                inicio=reserva.retirada_em,
                fim=reserva.devolucao_em,
                statuses=_BLOCKING_RESERVA_STATUSES,
                veiculo_id=reserva.veiculo_id,
                exclude_reserva_id=reserva.id,
            )
            if conflitos:
                raise ConflictError(
                    "Veículo indisponível no período da reserva.",
                    code="veiculo_indisponivel",
                )
            await self.veiculo_svc.change_status(
                reserva.veiculo_id, VeiculoStatus.RESERVADO
            )

        reserva.status = ReservaStatus.CONFIRMADA
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"Reserva confirmada: {reserva.numero}",
        )
        return reserva

    async def aprovar_bloqueado(self, reserva_id: uuid.UUID) -> ResReserva:
        reserva = await self.get(reserva_id)
        if not reserva.requer_aprovacao:
            raise BusinessRuleError("Reserva não requer aprovação.")
        if reserva.status != ReservaStatus.PENDENTE:
            raise BusinessRuleError("Somente reservas pendentes podem ser aprovadas.")

        reserva.requer_aprovacao = False
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"Aprovação de cliente bloqueado: {reserva.numero}",
        )
        return reserva

    async def cancelar(
        self, reserva_id: uuid.UUID, data: ReservaCancelInput
    ) -> ResReserva:
        reserva = await self.get(reserva_id)
        if reserva.status in {
            ReservaStatus.CANCELADA,
            ReservaStatus.NO_SHOW,
            ReservaStatus.CHECKOUT,
            ReservaStatus.CONCLUIDA,
        }:
            raise BusinessRuleError("Reserva não pode ser cancelada neste status.")

        valor_retencao = _ZERO
        if reserva.politica_cancelamento_id:
            horas_antes = max(
                0,
                int((reserva.retirada_em - datetime.now(tz=UTC)).total_seconds() / 3600),
            )
            sim = await self.pricing.simular_cancelamento(
                reserva.politica_cancelamento_id,
                reserva.valor_total,
                horas_antes,
                diaria_unitaria=reserva.diaria_unitaria,
                dias_locacao=reserva.dias,
            )
            valor_retencao = sim.valor_retencao

        await self._liberar_veiculo(reserva)
        reserva.status = ReservaStatus.CANCELADA
        reserva.motivo_cancelamento = data.motivo
        reserva.valor_retencao = valor_retencao
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"Reserva cancelada: {reserva.numero} (retenção={valor_retencao})",
        )
        return reserva

    async def marcar_no_show(self, reserva_id: uuid.UUID) -> ResReserva:
        reserva = await self.get(reserva_id)
        if reserva.status != ReservaStatus.CONFIRMADA:
            raise BusinessRuleError("Somente reservas confirmadas podem virar no-show.")

        valor_retencao = _ZERO
        if reserva.politica_cancelamento_id:
            sim = await self.pricing.simular_cancelamento(
                reserva.politica_cancelamento_id,
                reserva.valor_total,
                0,
                diaria_unitaria=reserva.diaria_unitaria,
                dias_locacao=reserva.dias,
            )
            valor_retencao = sim.valor_retencao

        await self._liberar_veiculo(reserva)
        reserva.status = ReservaStatus.NO_SHOW
        reserva.valor_retencao = valor_retencao
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"No-show registrado: {reserva.numero}",
        )
        return reserva

    async def create_contrato(self, reserva_id: uuid.UUID):
        """Gera contrato AGUARDANDO_CHECKOUT a partir de reserva confirmada."""
        reserva = await self.get(reserva_id)
        if reserva.status != ReservaStatus.CONFIRMADA:
            raise BusinessRuleError(
                "Somente reservas confirmadas geram contrato.",
                code="reserva_nao_confirmada",
            )
        from app.modules.locacoes.service import ContratoService

        return await ContratoService(self.session).from_reserva(reserva_id)

    async def checkout_realizado(self, reserva_id: uuid.UUID) -> ResReserva:
        reserva = await self.get(reserva_id)
        if reserva.status != ReservaStatus.CONFIRMADA:
            raise BusinessRuleError(
                "Check-out só pode ser registrado em reserva confirmada."
            )
        reserva.status = ReservaStatus.CHECKOUT
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"Check-out realizado: {reserva.numero}",
        )
        return reserva

    async def _get_cliente(self, cliente_id: uuid.UUID) -> Cliente:
        stmt = select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.deleted_at.is_(None),
        )
        cliente = (await self.session.execute(stmt)).scalar_one_or_none()
        if cliente is None:
            raise NotFoundError("Cliente não encontrado.")
        return cliente

    async def _assert_veiculo_disponivel(
        self,
        veiculo_id: uuid.UUID,
        filial_id: uuid.UUID,
        categoria_id: uuid.UUID,
        inicio: datetime,
        fim: datetime,
    ) -> None:
        veiculo = await self.veiculo_svc.get(veiculo_id)
        if veiculo.filial_id != filial_id:
            raise ValidationError("Veículo não pertence à filial de retirada.")
        if veiculo.categoria_id != categoria_id:
            raise ValidationError("Veículo não pertence à categoria selecionada.")
        if veiculo.status in _EXCLUDED_STATUSES:
            raise ConflictError("Veículo indisponível para reserva.", code="veiculo_indisponivel")

        disp = await self.disponibilidade.consultar(
            filial_id, inicio, fim, categoria_id=categoria_id
        )
        for cat in disp:
            for v in cat.veiculos:
                if v.id == veiculo_id and not v.disponivel:
                    raise ConflictError(
                        "Veículo indisponível no período.",
                        code="veiculo_indisponivel",
                    )

    def _build_pricing_input(
        self, tenant_id: uuid.UUID, data: ReservaCreate
    ) -> PricingQuoteInput:
        return PricingQuoteInput(
            tenant_id=tenant_id,
            filial_id=data.filial_retirada_id,
            categoria_id=data.categoria_id,
            canal=_origem_canal(data.origem),
            retirada_em=data.retirada_em,
            devolucao_em=data.devolucao_em,
            veiculo_id=data.veiculo_id,
            cliente_id=data.cliente_id,
            parceiro_id=data.parceiro_id,
            protecao_ids=data.protecao_ids,
            taxa_ids=data.taxa_ids,
            acessorio_ids=data.acessorio_ids,
            one_way=data.filial_retirada_id != data.filial_devolucao_id,
        )

    async def _sync_itens(
        self, tenant_id: uuid.UUID, reserva_id: uuid.UUID, quote
    ) -> None:
        for line in quote.taxas + quote.protecoes + quote.acessorios:
            item = _line_to_item(reserva_id, tenant_id, line)
            self.item_repo.add(item)
        await self.item_repo.flush()

    async def _sync_motoristas(
        self, tenant_id: uuid.UUID, reserva_id: uuid.UUID, motoristas
    ) -> None:
        if not motoristas:
            return
        has_principal = any(m.principal for m in motoristas)
        for idx, mot in enumerate(motoristas):
            principal = mot.principal or (not has_principal and idx == 0)
            row = ResReservaMotorista(
                tenant_id=tenant_id,
                reserva_id=reserva_id,
                motorista_id=mot.motorista_id,
                principal=principal,
            )
            self.motorista_repo.add(row)
        await self.motorista_repo.flush()

    async def _liberar_veiculo(self, reserva: ResReserva) -> None:
        if not reserva.veiculo_id:
            return
        veiculo = await self.veiculo_svc.get(reserva.veiculo_id)
        if veiculo.status == VeiculoStatus.RESERVADO:
            await self.veiculo_svc.change_status(
                reserva.veiculo_id, VeiculoStatus.DISPONIVEL
            )


class CotacaoService:
    """Cotações sem compromisso (§5.5)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CotacaoRepository(session)
        self.pricing = PricingService(session)
        self.reserva_svc = ReservaService(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"COT-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: CotacaoStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Page[ResCotacao]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(status=status, cliente_id=cliente_id, search=search),
        )

    async def get(self, cotacao_id: uuid.UUID) -> ResCotacao:
        item = await self.repo.get(cotacao_id)
        if item is None:
            raise NotFoundError("Cotação não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: CotacaoCreate) -> ResCotacao:
        pricing_input = PricingQuoteInput(
            tenant_id=tenant_id,
            filial_id=data.filial_retirada_id,
            categoria_id=data.categoria_id,
            canal=data.canal,
            retirada_em=data.retirada_em,
            devolucao_em=data.devolucao_em,
            veiculo_id=data.veiculo_id,
            cliente_id=data.cliente_id,
            parceiro_id=data.parceiro_id,
            protecao_ids=data.protecao_ids,
            taxa_ids=data.taxa_ids,
            acessorio_ids=data.acessorio_ids,
            one_way=data.filial_retirada_id != data.filial_devolucao_id,
        )
        quote = await self.pricing.calcular(pricing_input)
        fields = _pricing_to_reserva_fields(quote)

        cotacao = ResCotacao(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            status=CotacaoStatus.ABERTA,
            validade_em=datetime.now(tz=UTC) + timedelta(hours=data.validade_horas),
            filial_retirada_id=data.filial_retirada_id,
            filial_devolucao_id=data.filial_devolucao_id,
            categoria_id=data.categoria_id,
            veiculo_id=data.veiculo_id,
            retirada_em=data.retirada_em,
            devolucao_em=data.devolucao_em,
            cliente_id=data.cliente_id,
            origem=data.origem,
            parceiro_id=data.parceiro_id,
            observacoes=data.observacoes,
            **fields,
        )
        self.repo.add(cotacao)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="res_cotacao",
            entity_id=cotacao.id,
            description=f"Cotação criada: {cotacao.numero}",
        )
        # Hook §7.1: cria/atualiza oportunidade no funil (estágio cotação enviada).
        try:
            from app.modules.comercial.service import FunilService

            await FunilService(self.session).from_cotacao(cotacao)
        except Exception:  # noqa: BLE001 - o funil não deve bloquear a cotação
            pass
        return cotacao

    async def update(self, cotacao_id: uuid.UUID, data: CotacaoUpdate) -> ResCotacao:
        cotacao = await self.get(cotacao_id)
        if cotacao.status != CotacaoStatus.ABERTA:
            raise BusinessRuleError("Somente cotações abertas podem ser editadas.")

        payload = data.model_dump(exclude_unset=True)
        protecao_ids = payload.pop("protecao_ids", None)
        taxa_ids = payload.pop("taxa_ids", None)
        acessorio_ids = payload.pop("acessorio_ids", None)
        validade_horas = payload.pop("validade_horas", None)
        canal = payload.pop("canal", None)

        for key, value in payload.items():
            setattr(cotacao, key, value)

        if validade_horas is not None:
            cotacao.validade_em = datetime.now(tz=UTC) + timedelta(hours=validade_horas)

        recalc = any(
            k in data.model_dump(exclude_unset=True)
            for k in (
                "filial_retirada_id",
                "filial_devolucao_id",
                "categoria_id",
                "retirada_em",
                "devolucao_em",
                "veiculo_id",
                "cliente_id",
                "parceiro_id",
            )
        ) or protecao_ids is not None or taxa_ids is not None or acessorio_ids is not None

        if recalc:
            create_like = CotacaoCreate(
                filial_retirada_id=cotacao.filial_retirada_id,
                filial_devolucao_id=cotacao.filial_devolucao_id,
                categoria_id=cotacao.categoria_id,
                retirada_em=cotacao.retirada_em,
                devolucao_em=cotacao.devolucao_em,
                origem=cotacao.origem,
                canal=canal or TarifarioCanal.BALCAO,
                cliente_id=cotacao.cliente_id,
                veiculo_id=cotacao.veiculo_id,
                parceiro_id=cotacao.parceiro_id,
                protecao_ids=protecao_ids or [],
                taxa_ids=taxa_ids or [],
                acessorio_ids=acessorio_ids or [],
                observacoes=cotacao.observacoes,
            )
            pricing_input = PricingQuoteInput(
                tenant_id=cotacao.tenant_id,
                filial_id=create_like.filial_retirada_id,
                categoria_id=create_like.categoria_id,
                canal=create_like.canal,
                retirada_em=create_like.retirada_em,
                devolucao_em=create_like.devolucao_em,
                veiculo_id=create_like.veiculo_id,
                cliente_id=create_like.cliente_id,
                parceiro_id=create_like.parceiro_id,
                protecao_ids=create_like.protecao_ids,
                taxa_ids=create_like.taxa_ids,
                acessorio_ids=create_like.acessorio_ids,
                one_way=create_like.filial_retirada_id != create_like.filial_devolucao_id,
            )
            quote = await self.pricing.calcular(pricing_input)
            fields = _pricing_to_reserva_fields(quote)
            for key, value in fields.items():
                setattr(cotacao, key, value)

        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_cotacao",
            entity_id=cotacao.id,
            description=f"Cotação atualizada: {cotacao.numero}",
        )
        return cotacao

    async def delete(self, cotacao_id: uuid.UUID) -> None:
        cotacao = await self.get(cotacao_id)
        if cotacao.status == CotacaoStatus.CONVERTIDA:
            raise BusinessRuleError("Cotação convertida não pode ser excluída.")
        cotacao.status = CotacaoStatus.CANCELADA
        await self.repo.delete(cotacao)
        await audit_service.record(
            AuditAction.DELETE,
            entity="res_cotacao",
            entity_id=cotacao.id,
            description=f"Cotação excluída: {cotacao.numero}",
        )

    async def converter_em_reserva(
        self,
        cotacao_id: uuid.UUID,
        data: CotacaoConverterInput,
    ) -> ResReserva:
        cotacao = await self.get(cotacao_id)
        if cotacao.status != CotacaoStatus.ABERTA:
            raise BusinessRuleError("Cotação não está aberta para conversão.")
        if cotacao.validade_em < datetime.now(tz=UTC):
            raise BusinessRuleError("Cotação expirada.")

        snapshot = json.loads(cotacao.pricing_snapshot or "{}")
        input_data = snapshot.get("input", {})

        reserva_data = ReservaCreate(
            cliente_id=data.cliente_id,
            categoria_id=cotacao.categoria_id,
            filial_retirada_id=cotacao.filial_retirada_id,
            filial_devolucao_id=cotacao.filial_devolucao_id,
            retirada_em=cotacao.retirada_em,
            devolucao_em=cotacao.devolucao_em,
            origem=cotacao.origem,
            veiculo_id=cotacao.veiculo_id,
            parceiro_id=cotacao.parceiro_id,
            vendedor_id=data.vendedor_id,
            forma_pagamento_prevista=data.forma_pagamento_prevista,
            politica_cancelamento_id=data.politica_cancelamento_id,
            observacoes=data.observacoes or cotacao.observacoes,
            motoristas=data.motoristas,
            protecao_ids=input_data.get("protecao_ids", []),
            taxa_ids=input_data.get("taxa_ids", []),
            acessorio_ids=input_data.get("acessorio_ids", []),
            desconto=cotacao.desconto,
        )
        reserva = await self.reserva_svc.create(cotacao.tenant_id, reserva_data)

        cotacao.status = CotacaoStatus.CONVERTIDA
        cotacao.converted_reserva_id = reserva.id
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_cotacao",
            entity_id=cotacao.id,
            description=f"Cotação convertida em reserva {reserva.numero}",
        )
        # Hook §7.1: fecha a oportunidade como ganha e vincula a reserva gerada.
        try:
            from app.modules.comercial.service import FunilService

            await FunilService(self.session).marcar_ganho_por_cotacao(cotacao.id, reserva.id)
        except Exception:  # noqa: BLE001 - o funil não deve bloquear a conversão
            pass
        return reserva

    async def expirar_vencidas(self) -> int:
        """Marca cotações abertas vencidas como EXPIRADA."""
        now = datetime.now(tz=UTC)
        stmt = select(ResCotacao).where(
            ResCotacao.status == CotacaoStatus.ABERTA,
            ResCotacao.validade_em < now,
            ResCotacao.deleted_at.is_(None),
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        for cotacao in rows:
            cotacao.status = CotacaoStatus.EXPIRADA
        if rows:
            await self.repo.flush()
        return len(rows)


class CalendarioService:
    """Visão calendário/gantt de reservas (§5.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reserva_repo = ReservaRepository(session)
        self.disponibilidade = DisponibilidadeService(session)

    async def list_events(
        self,
        inicio: datetime,
        fim: datetime,
        *,
        filial_id: uuid.UUID | None = None,
        categoria_id: uuid.UUID | None = None,
        veiculo_id: uuid.UUID | None = None,
    ) -> list[CalendarioEvento]:
        stmt = self.reserva_repo._base_query().where(
            ResReserva.retirada_em < fim,
            ResReserva.devolucao_em > inicio,
            ResReserva.status.not_in(
                {ReservaStatus.CANCELADA, ReservaStatus.NO_SHOW}
            ),
        )
        if filial_id:
            stmt = stmt.where(ResReserva.filial_retirada_id == filial_id)
        if categoria_id:
            stmt = stmt.where(ResReserva.categoria_id == categoria_id)
        if veiculo_id:
            stmt = stmt.where(ResReserva.veiculo_id == veiculo_id)

        reservas = list((await self.session.execute(stmt)).scalars().all())
        return [
            CalendarioEvento(
                reserva_id=r.id,
                veiculo_id=r.veiculo_id,
                categoria_id=r.categoria_id,
                start=r.retirada_em,
                end=r.devolucao_em,
                status=r.status,
                numero=r.numero,
            )
            for r in reservas
        ]

    async def realocar(
        self, reserva_id: uuid.UUID, novo_veiculo_id: uuid.UUID
    ) -> ResReserva:
        reserva = await self.reserva_repo.get(reserva_id)
        if reserva is None:
            raise NotFoundError("Reserva não encontrada.")
        if reserva.status not in {ReservaStatus.PENDENTE, ReservaStatus.CONFIRMADA}:
            raise BusinessRuleError("Reserva não pode ser realocada neste status.")

        veiculo_svc = VeiculoService(self.session)
        veiculo = await veiculo_svc.get(novo_veiculo_id)
        if veiculo.categoria_id != reserva.categoria_id:
            raise ValidationError("Veículo deve ser da mesma categoria da reserva.")

        conflitos = await self.reserva_repo.overlapping_for_period(
            inicio=reserva.retirada_em,
            fim=reserva.devolucao_em,
            statuses=_BLOCKING_RESERVA_STATUSES,
            veiculo_id=novo_veiculo_id,
            exclude_reserva_id=reserva.id,
        )
        if conflitos:
            raise ConflictError(
                "Veículo possui conflito de reserva no período.",
                code="conflito_realocacao",
            )

        disp = await self.disponibilidade.consultar(
            reserva.filial_retirada_id,
            reserva.retirada_em,
            reserva.devolucao_em,
            categoria_id=reserva.categoria_id,
        )
        disponivel = any(
            v.id == novo_veiculo_id and v.disponivel for cat in disp for v in cat.veiculos
        )
        if not disponivel and reserva.status == ReservaStatus.CONFIRMADA:
            raise ConflictError(
                "Veículo indisponível para realocação.",
                code="veiculo_indisponivel",
            )

        veiculo_anterior = reserva.veiculo_id
        if veiculo_anterior and reserva.status == ReservaStatus.CONFIRMADA:
            ant = await veiculo_svc.get(veiculo_anterior)
            if ant.status == VeiculoStatus.RESERVADO:
                await veiculo_svc.change_status(
                    veiculo_anterior, VeiculoStatus.DISPONIVEL
                )

        reserva.veiculo_id = novo_veiculo_id
        reserva.alocacao = ReservaAlocacao.VEICULO

        if reserva.status == ReservaStatus.CONFIRMADA:
            await veiculo_svc.change_status(novo_veiculo_id, VeiculoStatus.RESERVADO)

        await self.reserva_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="res_reserva",
            entity_id=reserva.id,
            description=f"Reserva {reserva.numero} realocada para veículo {veiculo.placa}",
        )
        return reserva
