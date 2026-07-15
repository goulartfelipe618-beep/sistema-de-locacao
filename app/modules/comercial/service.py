"""Serviços de negócio do módulo Comercial / CRM (§7.1–7.5)."""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.comercial.models import (
    CrmCampanha,
    CrmCupom,
    CrmCupomUso,
    CrmFidelidadeConta,
    CrmFidelidadeMovimento,
    CrmFidelidadeRegra,
    CrmFidelidadeTier,
    CrmOportunidade,
    CrmOportunidadeInteracao,
    CrmProposta,
    CrmPropostaItem,
)
from app.modules.comercial.schemas import (
    CampanhaCreate,
    CampanhaUpdate,
    CupomCreate,
    CupomUpdate,
    CupomValidacaoResult,
    CupomValidarInput,
    FidelidadeRegraInput,
    FidelidadeTierInput,
    InteracaoCreate,
    OportunidadeCreate,
    OportunidadeUpdate,
    PropostaCreate,
    PropostaItemInput,
    PropostaUpdate,
)
from app.shared.enums import (
    AuditAction,
    CrmCampanhaPublico,
    CrmCampanhaStatus,
    CrmCupomStatus,
    CrmCupomTipo,
    CrmEstagio,
    CrmFidelidadeMovimentoTipo,
    CrmFidelidadeOrigem,
    CrmPropostaStatus,
)
from app.shared.repository import BaseRepository

_MONEY = Decimal("0.01")
_ZERO = Decimal("0")

# Colunas do quadro kanban (ordem de exibição).
KANBAN_ESTAGIOS: tuple[CrmEstagio, ...] = (
    CrmEstagio.LEAD,
    CrmEstagio.QUALIFICACAO,
    CrmEstagio.COTACAO_ENVIADA,
    CrmEstagio.NEGOCIACAO,
    CrmEstagio.FECHADO_GANHO,
    CrmEstagio.PERDIDO,
)

_ESTAGIOS_ABERTOS = {
    CrmEstagio.LEAD,
    CrmEstagio.QUALIFICACAO,
    CrmEstagio.COTACAO_ENVIADA,
    CrmEstagio.NEGOCIACAO,
}
_ESTAGIOS_FECHADOS = {CrmEstagio.FECHADO_GANHO, CrmEstagio.PERDIDO}

PROPOSTA_STATUS_EDITAVEL = {CrmPropostaStatus.RASCUNHO}


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_MONEY)


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ------------------------------------------------------------- Repositories
class OportunidadeRepository(BaseRepository[CrmOportunidade]):
    model = CrmOportunidade

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(CrmOportunidade)
            .where(CrmOportunidade.tenant_id == tenant_id, CrmOportunidade.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        estagio: CrmEstagio | None = None,
        vendedor_id: uuid.UUID | None = None,
        cliente_id: uuid.UUID | None = None,
    ) -> Select[tuple[CrmOportunidade]]:
        stmt = self._base_query().order_by(CrmOportunidade.created_at.desc())
        if estagio:
            stmt = stmt.where(CrmOportunidade.estagio == estagio)
        if vendedor_id:
            stmt = stmt.where(CrmOportunidade.vendedor_id == vendedor_id)
        if cliente_id:
            stmt = stmt.where(CrmOportunidade.cliente_id == cliente_id)
        return stmt

    async def get_by_cotacao(self, cotacao_id: uuid.UUID) -> CrmOportunidade | None:
        stmt = self._base_query().where(CrmOportunidade.cotacao_id == cotacao_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class InteracaoRepository(BaseRepository[CrmOportunidadeInteracao]):
    model = CrmOportunidadeInteracao

    def list_by_oportunidade(
        self, oportunidade_id: uuid.UUID
    ) -> Select[tuple[CrmOportunidadeInteracao]]:
        return (
            self._base_query()
            .where(CrmOportunidadeInteracao.oportunidade_id == oportunidade_id)
            .order_by(CrmOportunidadeInteracao.ocorrido_em.desc())
        )


class PropostaRepository(BaseRepository[CrmProposta]):
    model = CrmProposta

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(CrmProposta)
            .where(
                CrmProposta.tenant_id == tenant_id,
                CrmProposta.deleted_at.is_(None),
                CrmProposta.proposta_pai_id.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self, *, status: CrmPropostaStatus | None = None, cliente_id: uuid.UUID | None = None
    ) -> Select[tuple[CrmProposta]]:
        stmt = self._base_query().order_by(CrmProposta.created_at.desc())
        if status:
            stmt = stmt.where(CrmProposta.status == status)
        if cliente_id:
            stmt = stmt.where(CrmProposta.cliente_id == cliente_id)
        return stmt


class PropostaItemRepository(BaseRepository[CrmPropostaItem]):
    model = CrmPropostaItem

    def list_by_proposta(self, proposta_id: uuid.UUID) -> Select[tuple[CrmPropostaItem]]:
        return (
            self._base_query()
            .where(CrmPropostaItem.proposta_id == proposta_id)
            .order_by(CrmPropostaItem.created_at.asc())
        )

    async def delete_by_proposta(self, proposta_id: uuid.UUID) -> None:
        stmt = select(CrmPropostaItem).where(
            CrmPropostaItem.proposta_id == proposta_id,
            CrmPropostaItem.deleted_at.is_(None),
        )
        for row in (await self.session.execute(stmt)).scalars().all():
            await self.delete(row)


class CampanhaRepository(BaseRepository[CrmCampanha]):
    model = CrmCampanha

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(CrmCampanha)
            .where(CrmCampanha.tenant_id == tenant_id, CrmCampanha.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self, *, status: CrmCampanhaStatus | None = None
    ) -> Select[tuple[CrmCampanha]]:
        stmt = self._base_query().order_by(CrmCampanha.created_at.desc())
        if status:
            stmt = stmt.where(CrmCampanha.status == status)
        return stmt


class CupomRepository(BaseRepository[CrmCupom]):
    model = CrmCupom

    def list_query(self, *, status: CrmCupomStatus | None = None) -> Select[tuple[CrmCupom]]:
        stmt = self._base_query().order_by(CrmCupom.created_at.desc())
        if status:
            stmt = stmt.where(CrmCupom.status == status)
        return stmt

    async def get_by_codigo(self, codigo: str) -> CrmCupom | None:
        stmt = self._base_query().where(func.lower(CrmCupom.codigo) == codigo.strip().lower()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class CupomUsoRepository(BaseRepository[CrmCupomUso]):
    model = CrmCupomUso

    async def count_by_cupom(self, cupom_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(CrmCupomUso)
            .where(CrmCupomUso.cupom_id == cupom_id, CrmCupomUso.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_by_cupom_cliente(self, cupom_id: uuid.UUID, cliente_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(CrmCupomUso)
            .where(
                CrmCupomUso.cupom_id == cupom_id,
                CrmCupomUso.cliente_id == cliente_id,
                CrmCupomUso.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()


class FidelidadeRegraRepository(BaseRepository[CrmFidelidadeRegra]):
    model = CrmFidelidadeRegra

    async def get_ativa(self) -> CrmFidelidadeRegra | None:
        stmt = (
            self._base_query()
            .where(CrmFidelidadeRegra.ativo.is_(True))
            .order_by(CrmFidelidadeRegra.created_at.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class FidelidadeTierRepository(BaseRepository[CrmFidelidadeTier]):
    model = CrmFidelidadeTier

    def list_query(self) -> Select[tuple[CrmFidelidadeTier]]:
        return self._base_query().order_by(CrmFidelidadeTier.ordem.asc())


class FidelidadeContaRepository(BaseRepository[CrmFidelidadeConta]):
    model = CrmFidelidadeConta

    async def get_by_cliente(self, cliente_id: uuid.UUID) -> CrmFidelidadeConta | None:
        stmt = self._base_query().where(CrmFidelidadeConta.cliente_id == cliente_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_query(self) -> Select[tuple[CrmFidelidadeConta]]:
        return self._base_query().order_by(CrmFidelidadeConta.pontos_saldo.desc())


class FidelidadeMovimentoRepository(BaseRepository[CrmFidelidadeMovimento]):
    model = CrmFidelidadeMovimento

    def list_by_conta(self, conta_id: uuid.UUID) -> Select[tuple[CrmFidelidadeMovimento]]:
        return (
            self._base_query()
            .where(CrmFidelidadeMovimento.conta_id == conta_id)
            .order_by(CrmFidelidadeMovimento.created_at.desc())
        )


# =========================================================== 7.1 Funil de Vendas
class FunilService:
    """Gestão do funil de vendas / oportunidades (§7.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OportunidadeRepository(session)
        self.interacao_repo = InteracaoRepository(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"OPP-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        estagio: CrmEstagio | None = None,
        vendedor_id: uuid.UUID | None = None,
        cliente_id: uuid.UUID | None = None,
    ) -> Page[CrmOportunidade]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(
                estagio=estagio, vendedor_id=vendedor_id, cliente_id=cliente_id
            ),
        )

    async def get(self, oportunidade_id: uuid.UUID) -> CrmOportunidade:
        item = await self.repo.get(oportunidade_id)
        if item is None:
            raise NotFoundError("Oportunidade não encontrada.")
        return item

    async def kanban(self) -> dict[CrmEstagio, list[CrmOportunidade]]:
        """Retorna oportunidades agrupadas por estágio para o quadro kanban."""
        stmt = self.repo._base_query().order_by(CrmOportunidade.created_at.desc())
        rows = list((await self.session.execute(stmt)).scalars().all())
        board: dict[CrmEstagio, list[CrmOportunidade]] = {e: [] for e in KANBAN_ESTAGIOS}
        for opp in rows:
            board.setdefault(opp.estagio, []).append(opp)
        return board

    async def list_interacoes(
        self, oportunidade_id: uuid.UUID
    ) -> list[CrmOportunidadeInteracao]:
        stmt = self.interacao_repo.list_by_oportunidade(oportunidade_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, tenant_id: uuid.UUID, data: OportunidadeCreate) -> CrmOportunidade:
        opp = CrmOportunidade(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            titulo=data.titulo,
            estagio=data.estagio,
            origem_lead=data.origem_lead,
            vendedor_id=data.vendedor_id,
            cliente_id=data.cliente_id,
            cotacao_id=data.cotacao_id,
            reserva_id=data.reserva_id,
            valor_estimado=_money(data.valor_estimado),
            data_prevista_fechamento=data.data_prevista_fechamento,
            estagio_changed_at=_now(),
            observacoes=data.observacoes,
        )
        self.repo.add(opp)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="crm_oportunidade",
            entity_id=opp.id,
            description=f"Oportunidade criada: {opp.numero} ({opp.titulo}).",
        )
        return opp

    async def update(
        self, oportunidade_id: uuid.UUID, data: OportunidadeUpdate
    ) -> CrmOportunidade:
        opp = await self.get(oportunidade_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            if key == "valor_estimado" and value is not None:
                value = _money(value)
            setattr(opp, key, value)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_oportunidade",
            entity_id=opp.id,
            description=f"Oportunidade atualizada: {opp.numero}.",
        )
        return opp

    async def move_estagio(
        self, oportunidade_id: uuid.UUID, novo: CrmEstagio
    ) -> CrmOportunidade:
        opp = await self.get(oportunidade_id)
        if opp.estagio == novo:
            return opp
        opp.estagio = novo
        opp.estagio_changed_at = _now()
        if novo == CrmEstagio.PERDIDO and not opp.motivo_perda:
            opp.motivo_perda = "Não informado"
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_oportunidade",
            entity_id=opp.id,
            description=f"Oportunidade {opp.numero} movida para {novo.value}.",
        )
        return opp

    async def add_interacao(
        self,
        oportunidade_id: uuid.UUID,
        data: InteracaoCreate,
        *,
        user_id: uuid.UUID | None = None,
    ) -> CrmOportunidadeInteracao:
        opp = await self.get(oportunidade_id)
        ocorrido = data.ocorrido_em or _now()
        interacao = CrmOportunidadeInteracao(
            tenant_id=opp.tenant_id,
            oportunidade_id=opp.id,
            tipo=data.tipo,
            descricao=data.descricao,
            ocorrido_em=ocorrido,
            user_id=user_id,
        )
        self.interacao_repo.add(interacao)
        opp.ultima_interacao_em = ocorrido
        await self.interacao_repo.flush()
        return interacao

    async def marcar_perdido(
        self, oportunidade_id: uuid.UUID, motivo: str
    ) -> CrmOportunidade:
        opp = await self.get(oportunidade_id)
        opp.estagio = CrmEstagio.PERDIDO
        opp.motivo_perda = motivo
        opp.estagio_changed_at = _now()
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_oportunidade",
            entity_id=opp.id,
            description=f"Oportunidade {opp.numero} marcada como perdida.",
        )
        return opp

    async def marcar_ganho(
        self, oportunidade_id: uuid.UUID, *, reserva_id: uuid.UUID | None = None
    ) -> CrmOportunidade:
        opp = await self.get(oportunidade_id)
        opp.estagio = CrmEstagio.FECHADO_GANHO
        opp.estagio_changed_at = _now()
        if reserva_id:
            opp.reserva_id = reserva_id
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_oportunidade",
            entity_id=opp.id,
            description=f"Oportunidade {opp.numero} marcada como ganha.",
        )
        return opp

    async def from_cotacao(self, cotacao) -> CrmOportunidade:
        """Cria/atualiza uma oportunidade em ``cotacao_enviada`` a partir de uma cotação."""
        existing = await self.repo.get_by_cotacao(cotacao.id)
        if existing is not None:
            if existing.estagio in _ESTAGIOS_ABERTOS:
                existing.estagio = CrmEstagio.COTACAO_ENVIADA
                existing.estagio_changed_at = _now()
                existing.valor_estimado = _money(cotacao.valor_total)
                await self.repo.flush()
            return existing
        opp = CrmOportunidade(
            tenant_id=cotacao.tenant_id,
            numero=await self.next_numero(cotacao.tenant_id),
            titulo=f"Cotação {cotacao.numero}",
            estagio=CrmEstagio.COTACAO_ENVIADA,
            origem_lead=CrmOrigemLead_from_reserva(cotacao),
            cliente_id=cotacao.cliente_id,
            cotacao_id=cotacao.id,
            valor_estimado=_money(cotacao.valor_total),
            estagio_changed_at=_now(),
        )
        self.repo.add(opp)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="crm_oportunidade",
            entity_id=opp.id,
            description=f"Oportunidade gerada da cotação {cotacao.numero}: {opp.numero}.",
        )
        return opp

    async def marcar_ganho_por_cotacao(
        self, cotacao_id: uuid.UUID, reserva_id: uuid.UUID
    ) -> CrmOportunidade | None:
        opp = await self.repo.get_by_cotacao(cotacao_id)
        if opp is None:
            return None
        return await self.marcar_ganho(opp.id, reserva_id=reserva_id)

    async def list_paradas(self, *, dias: int = 7) -> list[CrmOportunidade]:
        """Oportunidades abertas paradas há mais de ``dias`` sem interação."""
        limite = _now() - timedelta(days=dias)
        stmt = self.repo._base_query().where(
            CrmOportunidade.estagio.in_(_ESTAGIOS_ABERTOS),
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        paradas: list[CrmOportunidade] = []
        for opp in rows:
            referencia = opp.ultima_interacao_em or opp.estagio_changed_at or opp.created_at
            if referencia is not None and referencia < limite:
                paradas.append(opp)
        return paradas


def CrmOrigemLead_from_reserva(cotacao):  # noqa: N802 - helper deriva origem_lead
    """Mapeia a origem da cotação/reserva para uma origem de lead do CRM."""
    from app.shared.enums import CrmOrigemLead, ReservaOrigem

    origem = getattr(cotacao, "origem", None)
    mapping = {
        ReservaOrigem.WEBSITE: CrmOrigemLead.SITE,
        ReservaOrigem.APP: CrmOrigemLead.SITE,
        ReservaOrigem.TELEFONE: CrmOrigemLead.TELEFONE,
        ReservaOrigem.PARCEIRO: CrmOrigemLead.PARCEIRO,
        ReservaOrigem.BALCAO: CrmOrigemLead.OUTRO,
    }
    return mapping.get(origem, CrmOrigemLead.OUTRO)


# =========================================================== 7.2 Propostas
class PropostaService:
    """Gestão de propostas comerciais (§7.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PropostaRepository(session)
        self.item_repo = PropostaItemRepository(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"PROP-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: CrmPropostaStatus | None = None,
        cliente_id: uuid.UUID | None = None,
    ) -> Page[CrmProposta]:
        return await self.repo.paginate(
            params, stmt=self.repo.list_query(status=status, cliente_id=cliente_id)
        )

    async def get(self, proposta_id: uuid.UUID) -> CrmProposta:
        item = await self.repo.get(proposta_id)
        if item is None:
            raise NotFoundError("Proposta não encontrada.")
        return item

    async def list_proposta_itens(self, proposta_id: uuid.UUID) -> list[CrmPropostaItem]:
        stmt = self.item_repo.list_by_proposta(proposta_id)
        return list((await self.session.execute(stmt)).scalars().all())

    def _item_total(self, item: PropostaItemInput) -> Decimal:
        return _money(item.valor_unitario * item.quantidade * Decimal(item.dias))

    async def _sync_itens(
        self, tenant_id: uuid.UUID, proposta_id: uuid.UUID, itens: list[PropostaItemInput]
    ) -> Decimal:
        total = _ZERO
        for item in itens:
            valor_total = self._item_total(item)
            total += valor_total
            self.item_repo.add(
                CrmPropostaItem(
                    tenant_id=tenant_id,
                    proposta_id=proposta_id,
                    categoria_id=item.categoria_id,
                    veiculo_id=item.veiculo_id,
                    descricao=item.descricao,
                    quantidade=item.quantidade,
                    periodo_inicio=item.periodo_inicio,
                    periodo_fim=item.periodo_fim,
                    dias=item.dias,
                    valor_unitario=_money(item.valor_unitario),
                    valor_total=valor_total,
                )
            )
        await self.item_repo.flush()
        return _money(total)

    async def create(self, tenant_id: uuid.UUID, data: PropostaCreate) -> CrmProposta:
        proposta = CrmProposta(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            versao=1,
            cliente_id=data.cliente_id,
            oportunidade_id=data.oportunidade_id,
            vendedor_id=data.vendedor_id,
            campanha_id=data.campanha_id,
            cupom_id=data.cupom_id,
            filial_id=data.filial_id,
            status=CrmPropostaStatus.RASCUNHO,
            validade_em=data.validade_em,
            condicoes_comerciais=data.condicoes_comerciais,
            observacoes=data.observacoes,
            valor_total=_ZERO,
        )
        self.repo.add(proposta)
        await self.repo.flush()
        total = await self._sync_itens(tenant_id, proposta.id, data.itens)
        proposta.valor_total = total
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="crm_proposta",
            entity_id=proposta.id,
            description=f"Proposta criada: {proposta.numero} ({total}).",
        )
        return proposta

    async def update(self, proposta_id: uuid.UUID, data: PropostaUpdate) -> CrmProposta:
        proposta = await self.get(proposta_id)
        if proposta.status not in PROPOSTA_STATUS_EDITAVEL:
            raise BusinessRuleError("Somente propostas em rascunho podem ser editadas.")
        payload = data.model_dump(exclude_unset=True)
        itens = payload.pop("itens", None)
        for key, value in payload.items():
            setattr(proposta, key, value)
        if itens is not None:
            await self.item_repo.delete_by_proposta(proposta.id)
            proposta.valor_total = await self._sync_itens(
                proposta.tenant_id, proposta.id, [PropostaItemInput(**i) for i in itens]
            )
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_proposta",
            entity_id=proposta.id,
            description=f"Proposta atualizada: {proposta.numero}.",
        )
        return proposta

    async def enviar(self, proposta_id: uuid.UUID) -> CrmProposta:
        proposta = await self.get(proposta_id)
        if proposta.status not in {CrmPropostaStatus.RASCUNHO, CrmPropostaStatus.ENVIADA}:
            raise BusinessRuleError("Proposta não pode ser enviada neste status.")
        proposta.status = CrmPropostaStatus.ENVIADA
        proposta.enviada_em = _now()
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_proposta",
            entity_id=proposta.id,
            description=f"Proposta enviada: {proposta.numero}.",
        )
        return proposta

    async def marcar_visualizada(self, proposta_id: uuid.UUID) -> CrmProposta:
        proposta = await self.get(proposta_id)
        if proposta.status == CrmPropostaStatus.ENVIADA:
            proposta.status = CrmPropostaStatus.VISUALIZADA
            proposta.visualizada_em = _now()
            await self.repo.flush()
        return proposta

    async def aceitar(self, proposta_id: uuid.UUID) -> CrmProposta:
        proposta = await self.get(proposta_id)
        if proposta.status not in {
            CrmPropostaStatus.ENVIADA,
            CrmPropostaStatus.VISUALIZADA,
        }:
            raise BusinessRuleError("Somente propostas enviadas/visualizadas podem ser aceitas.")
        proposta.status = CrmPropostaStatus.ACEITA
        proposta.aceita_em = _now()
        await self.repo.flush()
        # Marca a oportunidade vinculada como ganha, se houver.
        if proposta.oportunidade_id:
            with contextlib.suppress(NotFoundError):
                await FunilService(self.session).marcar_ganho(proposta.oportunidade_id)
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_proposta",
            entity_id=proposta.id,
            description=f"Proposta aceita: {proposta.numero}.",
        )
        return proposta

    async def recusar(self, proposta_id: uuid.UUID) -> CrmProposta:
        proposta = await self.get(proposta_id)
        if proposta.status in {CrmPropostaStatus.ACEITA, CrmPropostaStatus.RECUSADA}:
            raise BusinessRuleError("Proposta não pode ser recusada neste status.")
        proposta.status = CrmPropostaStatus.RECUSADA
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_proposta",
            entity_id=proposta.id,
            description=f"Proposta recusada: {proposta.numero}.",
        )
        return proposta

    async def criar_revisao(self, proposta_id: uuid.UUID) -> CrmProposta:
        """Cria uma nova versão (revisão) copiando os itens da proposta original."""
        original = await self.get(proposta_id)
        pai_id = original.proposta_pai_id or original.id
        itens = await self.list_proposta_itens(proposta_id)
        nova = CrmProposta(
            tenant_id=original.tenant_id,
            numero=original.numero,
            versao=original.versao + 1,
            proposta_pai_id=pai_id,
            cliente_id=original.cliente_id,
            oportunidade_id=original.oportunidade_id,
            vendedor_id=original.vendedor_id,
            campanha_id=original.campanha_id,
            cupom_id=original.cupom_id,
            filial_id=original.filial_id,
            status=CrmPropostaStatus.RASCUNHO,
            validade_em=original.validade_em,
            condicoes_comerciais=original.condicoes_comerciais,
            observacoes=original.observacoes,
            valor_total=_ZERO,
        )
        self.repo.add(nova)
        await self.repo.flush()
        total = _ZERO
        for item in itens:
            total += item.valor_total
            self.item_repo.add(
                CrmPropostaItem(
                    tenant_id=nova.tenant_id,
                    proposta_id=nova.id,
                    categoria_id=item.categoria_id,
                    veiculo_id=item.veiculo_id,
                    descricao=item.descricao,
                    quantidade=item.quantidade,
                    periodo_inicio=item.periodo_inicio,
                    periodo_fim=item.periodo_fim,
                    dias=item.dias,
                    valor_unitario=item.valor_unitario,
                    valor_total=item.valor_total,
                )
            )
        nova.valor_total = _money(total)
        await self.item_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="crm_proposta",
            entity_id=nova.id,
            description=f"Revisão v{nova.versao} da proposta {nova.numero}.",
        )
        return nova

    async def delete(self, proposta_id: uuid.UUID) -> None:
        proposta = await self.get(proposta_id)
        if proposta.status == CrmPropostaStatus.ACEITA:
            raise BusinessRuleError("Proposta aceita não pode ser excluída.")
        await self.repo.delete(proposta)
        await audit_service.record(
            AuditAction.DELETE,
            entity="crm_proposta",
            entity_id=proposta.id,
            description=f"Proposta excluída: {proposta.numero}.",
        )

    async def expirar_vencidas(self, *, ref: date | None = None) -> int:
        """Job: marca propostas enviadas/visualizadas com validade vencida como EXPIRADA."""
        ref = ref or date.today()
        stmt = self.repo._base_query().where(
            CrmProposta.status.in_(
                {CrmPropostaStatus.ENVIADA, CrmPropostaStatus.VISUALIZADA}
            ),
            CrmProposta.validade_em.is_not(None),
            CrmProposta.validade_em < ref,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        for proposta in rows:
            proposta.status = CrmPropostaStatus.EXPIRADA
        if rows:
            await self.repo.flush()
        return len(rows)


# =========================================================== 7.3 Campanhas
class CampanhaService:
    """Gestão de campanhas de marketing (§7.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CampanhaRepository(session)

    async def next_codigo(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"CAMP-{count + 1:06d}"

    async def list_items(
        self, params: PageParams, *, status: CrmCampanhaStatus | None = None
    ) -> Page[CrmCampanha]:
        return await self.repo.paginate(params, stmt=self.repo.list_query(status=status))

    async def get(self, campanha_id: uuid.UUID) -> CrmCampanha:
        item = await self.repo.get(campanha_id)
        if item is None:
            raise NotFoundError("Campanha não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: CampanhaCreate) -> CrmCampanha:
        campanha = CrmCampanha(
            tenant_id=tenant_id,
            codigo=await self.next_codigo(tenant_id),
            status=CrmCampanhaStatus.RASCUNHO,
            **data.model_dump(),
        )
        self.repo.add(campanha)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="crm_campanha",
            entity_id=campanha.id,
            description=f"Campanha criada: {campanha.codigo} ({campanha.nome}).",
        )
        return campanha

    async def update(self, campanha_id: uuid.UUID, data: CampanhaUpdate) -> CrmCampanha:
        campanha = await self.get(campanha_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(campanha, key, value)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_campanha",
            entity_id=campanha.id,
            description=f"Campanha atualizada: {campanha.codigo}.",
        )
        return campanha

    async def _set_status(
        self, campanha_id: uuid.UUID, status: CrmCampanhaStatus, label: str
    ) -> CrmCampanha:
        campanha = await self.get(campanha_id)
        campanha.status = status
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_campanha",
            entity_id=campanha.id,
            description=f"Campanha {campanha.codigo} {label}.",
        )
        return campanha

    async def ativar(self, campanha_id: uuid.UUID) -> CrmCampanha:
        return await self._set_status(campanha_id, CrmCampanhaStatus.ATIVA, "ativada")

    async def pausar(self, campanha_id: uuid.UUID) -> CrmCampanha:
        return await self._set_status(campanha_id, CrmCampanhaStatus.PAUSADA, "pausada")

    async def encerrar(self, campanha_id: uuid.UUID) -> CrmCampanha:
        return await self._set_status(campanha_id, CrmCampanhaStatus.ENCERRADA, "encerrada")

    async def _segmentar(self, campanha: CrmCampanha) -> int:
        """Conta os clientes elegíveis conforme a segmentação da campanha."""
        from app.modules.cadastros.models import Cliente
        from app.shared.enums import ClienteStatus

        stmt = select(func.count()).select_from(Cliente).where(
            Cliente.deleted_at.is_(None),
            Cliente.status == ClienteStatus.ACTIVE,
        )
        if campanha.publico_alvo == CrmCampanhaPublico.CATEGORIA_CLIENTE and campanha.categoria_cliente:
            stmt = stmt.where(Cliente.categoria_codigo == campanha.categoria_cliente)
        return (await self.session.execute(stmt)).scalar_one()

    async def disparar(self, campanha_id: uuid.UUID) -> CrmCampanha:
        """Simula o disparo da campanha: incrementa a métrica de enviados."""
        campanha = await self.get(campanha_id)
        if campanha.status != CrmCampanhaStatus.ATIVA:
            raise BusinessRuleError("Somente campanhas ativas podem ser disparadas.")
        alvo = await self._segmentar(campanha)
        campanha.enviados += alvo
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_campanha",
            entity_id=campanha.id,
            description=f"Campanha {campanha.codigo} disparada para {alvo} clientes.",
        )
        return campanha

    async def registrar_conversao(self, campanha_id: uuid.UUID) -> CrmCampanha:
        campanha = await self.get(campanha_id)
        campanha.convertidos += 1
        await self.repo.flush()
        return campanha


# =========================================================== 7.4 Cupons
class CupomService:
    """Gestão e validação de cupons de desconto (§7.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CupomRepository(session)
        self.uso_repo = CupomUsoRepository(session)

    async def list_items(
        self, params: PageParams, *, status: CrmCupomStatus | None = None
    ) -> Page[CrmCupom]:
        return await self.repo.paginate(params, stmt=self.repo.list_query(status=status))

    async def get(self, cupom_id: uuid.UUID) -> CrmCupom:
        item = await self.repo.get(cupom_id)
        if item is None:
            raise NotFoundError("Cupom não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: CupomCreate) -> CrmCupom:
        existing = await self.repo.get_by_codigo(data.codigo)
        if existing is not None:
            raise ConflictError("Já existe um cupom com este código.", code="cupom_duplicado")
        cupom = CrmCupom(
            tenant_id=tenant_id,
            status=CrmCupomStatus.ATIVO,
            usos_totais=0,
            **data.model_dump(),
        )
        cupom.codigo = cupom.codigo.strip().upper()
        self.repo.add(cupom)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="crm_cupom",
            entity_id=cupom.id,
            description=f"Cupom criado: {cupom.codigo}.",
        )
        return cupom

    async def update(self, cupom_id: uuid.UUID, data: CupomUpdate) -> CrmCupom:
        cupom = await self.get(cupom_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(cupom, key, value)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_cupom",
            entity_id=cupom.id,
            description=f"Cupom atualizado: {cupom.codigo}.",
        )
        return cupom

    async def delete(self, cupom_id: uuid.UUID) -> None:
        cupom = await self.get(cupom_id)
        await self.repo.delete(cupom)
        await audit_service.record(
            AuditAction.DELETE,
            entity="crm_cupom",
            entity_id=cupom.id,
            description=f"Cupom excluído: {cupom.codigo}.",
        )

    def _calcular_desconto(self, cupom: CrmCupom, valor_base: Decimal) -> Decimal:
        if cupom.tipo == CrmCupomTipo.PERCENTUAL:
            desconto = valor_base * (cupom.valor / Decimal(100))
        else:
            desconto = cupom.valor
        return _money(min(desconto, valor_base))

    async def _refresh_status(self, cupom: CrmCupom, *, ref: date | None = None) -> None:
        ref = ref or date.today()
        if cupom.status == CrmCupomStatus.INATIVO:
            return
        if cupom.fim_em is not None and cupom.fim_em < ref:
            cupom.status = CrmCupomStatus.EXPIRADO
        elif cupom.limite_uso_total is not None and cupom.usos_totais >= cupom.limite_uso_total:
            cupom.status = CrmCupomStatus.ESGOTADO

    async def _primeira_locacao(self, cliente_id: uuid.UUID) -> bool:
        from app.modules.locacoes.models import LocContrato

        stmt = (
            select(func.count())
            .select_from(LocContrato)
            .where(LocContrato.cliente_id == cliente_id, LocContrato.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one() == 0

    async def validar(self, data: CupomValidarInput) -> CupomValidacaoResult:
        cupom = await self.repo.get_by_codigo(data.codigo)
        if cupom is None:
            return CupomValidacaoResult(ok=False, motivo="Cupom inexistente.")

        await self._refresh_status(cupom)
        await self.repo.flush()

        if cupom.status != CrmCupomStatus.ATIVO:
            return CupomValidacaoResult(
                ok=False, motivo=f"Cupom {cupom.status.value}.", cupom_id=cupom.id, codigo=cupom.codigo
            )

        hoje = date.today()
        if cupom.inicio_em is not None and cupom.inicio_em > hoje:
            return CupomValidacaoResult(
                ok=False, motivo="Cupom ainda não vigente.", cupom_id=cupom.id, codigo=cupom.codigo
            )
        if cupom.valor_minimo > _ZERO and data.valor_base < cupom.valor_minimo:
            return CupomValidacaoResult(
                ok=False,
                motivo=f"Valor mínimo de {cupom.valor_minimo} não atingido.",
                cupom_id=cupom.id,
                codigo=cupom.codigo,
            )
        if cupom.categoria_id is not None and data.categoria_id != cupom.categoria_id:
            return CupomValidacaoResult(
                ok=False,
                motivo="Cupom não elegível para a categoria selecionada.",
                cupom_id=cupom.id,
                codigo=cupom.codigo,
            )
        if cupom.limite_uso_total is not None:
            usos = await self.uso_repo.count_by_cupom(cupom.id)
            if usos >= cupom.limite_uso_total:
                cupom.status = CrmCupomStatus.ESGOTADO
                await self.repo.flush()
                return CupomValidacaoResult(
                    ok=False, motivo="Limite total de uso atingido.", cupom_id=cupom.id, codigo=cupom.codigo
                )
        if data.cliente_id is not None:
            if cupom.limite_uso_cliente is not None:
                usos_cli = await self.uso_repo.count_by_cupom_cliente(cupom.id, data.cliente_id)
                if usos_cli >= cupom.limite_uso_cliente:
                    return CupomValidacaoResult(
                        ok=False,
                        motivo="Limite de uso por cliente atingido.",
                        cupom_id=cupom.id,
                        codigo=cupom.codigo,
                    )
            if cupom.primeira_locacao_apenas and not await self._primeira_locacao(data.cliente_id):
                return CupomValidacaoResult(
                    ok=False,
                    motivo="Cupom exclusivo para primeira locação.",
                    cupom_id=cupom.id,
                    codigo=cupom.codigo,
                )
        elif cupom.primeira_locacao_apenas:
            return CupomValidacaoResult(
                ok=False,
                motivo="Cupom exige cliente identificado (primeira locação).",
                cupom_id=cupom.id,
                codigo=cupom.codigo,
            )

        desconto = self._calcular_desconto(cupom, data.valor_base)
        return CupomValidacaoResult(
            ok=True, desconto=desconto, cupom_id=cupom.id, codigo=cupom.codigo
        )

    async def aplicar(
        self,
        cupom_id: uuid.UUID,
        *,
        cliente_id: uuid.UUID | None,
        reserva_id: uuid.UUID | None,
        desconto_aplicado: Decimal,
    ) -> CrmCupomUso:
        cupom = await self.get(cupom_id)
        uso = CrmCupomUso(
            tenant_id=cupom.tenant_id,
            cupom_id=cupom.id,
            cliente_id=cliente_id,
            reserva_id=reserva_id,
            desconto_aplicado=_money(desconto_aplicado),
            usado_em=_now(),
        )
        self.uso_repo.add(uso)
        cupom.usos_totais += 1
        await self._refresh_status(cupom)
        await self.uso_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_cupom",
            entity_id=cupom.id,
            description=f"Cupom {cupom.codigo} aplicado (desconto {desconto_aplicado}).",
        )
        return uso


# =========================================================== 7.5 Fidelidade
class FidelidadeService:
    """Programa de fidelidade / pontos (§7.5)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.regra_repo = FidelidadeRegraRepository(session)
        self.tier_repo = FidelidadeTierRepository(session)
        self.conta_repo = FidelidadeContaRepository(session)
        self.mov_repo = FidelidadeMovimentoRepository(session)

    async def ensure_regra(self, tenant_id: uuid.UUID) -> CrmFidelidadeRegra:
        regra = await self.regra_repo.get_ativa()
        if regra is None:
            regra = CrmFidelidadeRegra(tenant_id=tenant_id)
            self.regra_repo.add(regra)
            await self.regra_repo.flush()
        return regra

    async def get_regra(self) -> CrmFidelidadeRegra | None:
        return await self.regra_repo.get_ativa()

    async def salvar_regra(
        self, tenant_id: uuid.UUID, data: FidelidadeRegraInput
    ) -> CrmFidelidadeRegra:
        regra = await self.regra_repo.get_ativa()
        if regra is None:
            regra = CrmFidelidadeRegra(tenant_id=tenant_id, **data.model_dump())
            self.regra_repo.add(regra)
        else:
            for key, value in data.model_dump().items():
                setattr(regra, key, value)
        await self.regra_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_fidelidade_regra",
            entity_id=regra.id,
            description="Regra de fidelidade salva.",
        )
        return regra

    async def list_tiers(self) -> list[CrmFidelidadeTier]:
        stmt = self.tier_repo.list_query()
        return list((await self.session.execute(stmt)).scalars().all())

    async def add_tier(
        self, tenant_id: uuid.UUID, data: FidelidadeTierInput
    ) -> CrmFidelidadeTier:
        tier = CrmFidelidadeTier(tenant_id=tenant_id, **data.model_dump())
        self.tier_repo.add(tier)
        await self.tier_repo.flush()
        return tier

    async def list_contas(self, params: PageParams) -> Page[CrmFidelidadeConta]:
        return await self.conta_repo.paginate(params, stmt=self.conta_repo.list_query())

    async def ensure_conta(
        self, tenant_id: uuid.UUID, cliente_id: uuid.UUID
    ) -> CrmFidelidadeConta:
        conta = await self.conta_repo.get_by_cliente(cliente_id)
        if conta is None:
            conta = CrmFidelidadeConta(
                tenant_id=tenant_id,
                cliente_id=cliente_id,
                pontos_saldo=0,
                pontos_historico_total=0,
            )
            self.conta_repo.add(conta)
            await self.conta_repo.flush()
        return conta

    async def get_conta_por_cliente(self, cliente_id: uuid.UUID) -> CrmFidelidadeConta | None:
        return await self.conta_repo.get_by_cliente(cliente_id)

    async def extrato(self, conta_id: uuid.UUID) -> list[CrmFidelidadeMovimento]:
        stmt = self.mov_repo.list_by_conta(conta_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def recalcular_tier(self, conta: CrmFidelidadeConta) -> CrmFidelidadeConta:
        tiers = await self.list_tiers()
        escolhido: CrmFidelidadeTier | None = None
        for tier in tiers:
            if conta.pontos_historico_total >= tier.pontos_minimos and (
                escolhido is None or tier.pontos_minimos >= escolhido.pontos_minimos
            ):
                escolhido = tier
        conta.tier_id = escolhido.id if escolhido else None
        await self.conta_repo.flush()
        return conta

    async def creditar_contrato(
        self,
        tenant_id: uuid.UUID,
        *,
        contrato_id: uuid.UUID,
        cliente_id: uuid.UUID,
        valor_total: Decimal,
        dias: int,
    ) -> CrmFidelidadeMovimento | None:
        regra = await self.regra_repo.get_ativa()
        if regra is None or not regra.ativo:
            return None
        pontos = int(
            (Decimal(valor_total) * regra.pontos_por_real)
            + (Decimal(dias) * regra.pontos_por_diaria)
        )
        if pontos <= 0:
            return None
        conta = await self.ensure_conta(tenant_id, cliente_id)
        # Evita crédito duplicado para o mesmo contrato.
        dup_stmt = self.mov_repo._base_query().where(
            CrmFidelidadeMovimento.conta_id == conta.id,
            CrmFidelidadeMovimento.origem == CrmFidelidadeOrigem.CONTRATO,
            CrmFidelidadeMovimento.origem_id == contrato_id,
        )
        if (await self.session.execute(dup_stmt)).scalar_one_or_none() is not None:
            return None
        expira = _now() + relativedelta(months=regra.validade_meses)
        movimento = CrmFidelidadeMovimento(
            tenant_id=tenant_id,
            conta_id=conta.id,
            tipo=CrmFidelidadeMovimentoTipo.CREDITO,
            pontos=pontos,
            origem=CrmFidelidadeOrigem.CONTRATO,
            origem_id=contrato_id,
            descricao=f"Crédito por contrato ({valor_total} / {dias} diárias).",
            saldo_restante=pontos,
            expira_em=expira,
        )
        self.mov_repo.add(movimento)
        conta.pontos_saldo += pontos
        conta.pontos_historico_total += pontos
        await self.mov_repo.flush()
        await self.recalcular_tier(conta)
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_fidelidade_conta",
            entity_id=conta.id,
            description=f"Crédito de {pontos} pontos (contrato {contrato_id}).",
        )
        return movimento

    async def resgatar(
        self,
        tenant_id: uuid.UUID,
        *,
        cliente_id: uuid.UUID,
        pontos: int,
        reserva_id: uuid.UUID | None = None,
    ) -> tuple[CrmFidelidadeMovimento, Decimal]:
        if pontos <= 0:
            raise ValidationError("Quantidade de pontos inválida.")
        conta = await self.ensure_conta(tenant_id, cliente_id)
        if conta.pontos_saldo < pontos:
            raise BusinessRuleError("Saldo de pontos insuficiente para resgate.")
        regra = await self.ensure_regra(tenant_id)
        valor = _money(Decimal(pontos) * regra.valor_por_ponto)

        # Consome saldo dos créditos mais antigos primeiro (FIFO).
        restante = pontos
        creditos_stmt = (
            self.mov_repo._base_query()
            .where(
                CrmFidelidadeMovimento.conta_id == conta.id,
                CrmFidelidadeMovimento.tipo == CrmFidelidadeMovimentoTipo.CREDITO,
                CrmFidelidadeMovimento.saldo_restante > 0,
            )
            .order_by(CrmFidelidadeMovimento.created_at.asc())
        )
        for credito in (await self.session.execute(creditos_stmt)).scalars().all():
            if restante <= 0:
                break
            consumir = min(credito.saldo_restante, restante)
            credito.saldo_restante -= consumir
            restante -= consumir

        movimento = CrmFidelidadeMovimento(
            tenant_id=tenant_id,
            conta_id=conta.id,
            tipo=CrmFidelidadeMovimentoTipo.DEBITO,
            pontos=pontos,
            origem=CrmFidelidadeOrigem.RESGATE,
            origem_id=reserva_id,
            descricao=f"Resgate de {pontos} pontos (R$ {valor}).",
            saldo_restante=0,
        )
        self.mov_repo.add(movimento)
        conta.pontos_saldo -= pontos
        await self.mov_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="crm_fidelidade_conta",
            entity_id=conta.id,
            description=f"Resgate de {pontos} pontos (R$ {valor}).",
        )
        return movimento, valor

    async def expirar_pontos(self, *, ref: datetime | None = None) -> int:
        """Job: expira créditos com validade vencida e saldo remanescente."""
        ref = ref or _now()
        stmt = self.mov_repo._base_query().where(
            CrmFidelidadeMovimento.tipo == CrmFidelidadeMovimentoTipo.CREDITO,
            CrmFidelidadeMovimento.saldo_restante > 0,
            CrmFidelidadeMovimento.expira_em.is_not(None),
            CrmFidelidadeMovimento.expira_em < ref,
        )
        creditos = list((await self.session.execute(stmt)).scalars().all())
        total_expirado = 0
        for credito in creditos:
            pontos = credito.saldo_restante
            if pontos <= 0:
                continue
            conta = await self.conta_repo.get(credito.conta_id)
            if conta is None:
                continue
            credito.saldo_restante = 0
            conta.pontos_saldo = max(0, conta.pontos_saldo - pontos)
            self.mov_repo.add(
                CrmFidelidadeMovimento(
                    tenant_id=credito.tenant_id,
                    conta_id=conta.id,
                    tipo=CrmFidelidadeMovimentoTipo.EXPIRACAO,
                    pontos=pontos,
                    origem=CrmFidelidadeOrigem.EXPIRACAO,
                    origem_id=credito.id,
                    descricao=f"Expiração de {pontos} pontos.",
                    saldo_restante=0,
                )
            )
            total_expirado += pontos
        if creditos:
            await self.mov_repo.flush()
        return total_expirado
