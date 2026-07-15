"""Serviços de negócio do módulo Financeiro (§9.1–9.8)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.financeiro.models import (
    FinCaixaLancamento,
    FinCaixaSessao,
    FinCartaoTransacao,
    FinContaBancaria,
    FinContaPagar,
    FinContaPagarBaixa,
    FinContaReceber,
    FinContaReceberBaixa,
    FinExtratoLinha,
    FinFatura,
    FinFaturamentoConfig,
    FinFaturaTitulo,
    FinPixChave,
    FinPixCobranca,
)
from app.modules.financeiro.schemas import (
    CaixaAbrirInput,
    CaixaFecharInput,
    CaixaLancamentoCreate,
    CartaoAutorizarInput,
    CartaoCapturarInput,
    ConsolidarInput,
    ContaBancariaCreate,
    ContaPagarCreate,
    ContaReceberCreate,
    FaturamentoConfigCreate,
    ManualMatchInput,
    OfxImportInput,
    PagarAprovarInput,
    PagarEfetivarInput,
    PixChaveCreate,
    PixCobrancaCreate,
    ReceberBaixaInput,
)
from app.shared.enums import (
    AuditAction,
    CaixaLancamentoTipo,
    CaixaSessaoStatus,
    CartaoTipo,
    CartaoTransacaoStatus,
    ConciliacaoStatus,
    ContaPagarOrigem,
    ContaReceberOrigem,
    ExtratoTipo,
    FaturaStatus,
    FormaPagamento,
    PixCobrancaStatus,
    TituloStatus,
)
from app.shared.repository import BaseRepository

_MONEY = Decimal("0.01")
_ZERO = Decimal("0")

_CREDIT_LANCAMENTOS = {CaixaLancamentoTipo.ENTRADA, CaixaLancamentoTipo.SUPRIMENTO}
_TITULO_ABERTO = {
    TituloStatus.EM_ABERTO,
    TituloStatus.VENCIDO,
    TituloStatus.PAGO_PARCIAL,
}
_TITULO_TERMINAL = {TituloStatus.PAGO, TituloStatus.CANCELADO, TituloStatus.ESTORNADO}

# Máquina de estados dos títulos financeiros (a receber / a pagar).
TITULO_TRANSITIONS: dict[TituloStatus, set[TituloStatus]] = {
    TituloStatus.EM_ABERTO: {
        TituloStatus.VENCIDO,
        TituloStatus.PAGO_PARCIAL,
        TituloStatus.PAGO,
        TituloStatus.CANCELADO,
    },
    TituloStatus.VENCIDO: {
        TituloStatus.PAGO_PARCIAL,
        TituloStatus.PAGO,
        TituloStatus.CANCELADO,
    },
    TituloStatus.PAGO_PARCIAL: {
        TituloStatus.PAGO,
        TituloStatus.VENCIDO,
        TituloStatus.ESTORNADO,
    },
    TituloStatus.PAGO: {TituloStatus.ESTORNADO},
    TituloStatus.CANCELADO: set(),
    TituloStatus.ESTORNADO: set(),
}

CARTAO_TRANSITIONS: dict[CartaoTransacaoStatus, set[CartaoTransacaoStatus]] = {
    CartaoTransacaoStatus.AUTORIZADO: {
        CartaoTransacaoStatus.CAPTURADO,
        CartaoTransacaoStatus.CANCELADO,
    },
    CartaoTransacaoStatus.CAPTURADO: {
        CartaoTransacaoStatus.LIQUIDADO,
        CartaoTransacaoStatus.ESTORNADO,
    },
    CartaoTransacaoStatus.LIQUIDADO: {CartaoTransacaoStatus.ESTORNADO},
    CartaoTransacaoStatus.CANCELADO: set(),
    CartaoTransacaoStatus.ESTORNADO: set(),
}

AGING_BUCKETS = ("a_vencer", "1-30", "31-60", "61-90", "90+")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_MONEY)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def aging_bucket(vencimento: date, ref: date | None = None) -> str:
    """Classifica um título em faixa de atraso (aging) a partir do vencimento."""
    ref = ref or date.today()
    if vencimento >= ref:
        return "a_vencer"
    dias = (ref - vencimento).days
    if dias <= 30:
        return "1-30"
    if dias <= 60:
        return "31-60"
    if dias <= 90:
        return "61-90"
    return "90+"


# ------------------------------------------------------------- Repositories
class CaixaSessaoRepository(BaseRepository[FinCaixaSessao]):
    model = FinCaixaSessao

    def list_query(
        self, *, status: CaixaSessaoStatus | None = None, filial_id: uuid.UUID | None = None
    ) -> Select[tuple[FinCaixaSessao]]:
        stmt = self._base_query().order_by(FinCaixaSessao.aberta_em.desc())
        if status:
            stmt = stmt.where(FinCaixaSessao.status == status)
        if filial_id:
            stmt = stmt.where(FinCaixaSessao.filial_id == filial_id)
        return stmt

    async def get_aberta(
        self, operador_id: uuid.UUID, filial_id: uuid.UUID
    ) -> FinCaixaSessao | None:
        stmt = (
            self._base_query()
            .where(
                FinCaixaSessao.operador_id == operador_id,
                FinCaixaSessao.filial_id == filial_id,
                FinCaixaSessao.status == CaixaSessaoStatus.ABERTA,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class CaixaLancamentoRepository(BaseRepository[FinCaixaLancamento]):
    model = FinCaixaLancamento

    def list_by_sessao(self, sessao_id: uuid.UUID) -> Select[tuple[FinCaixaLancamento]]:
        return (
            self._base_query()
            .where(FinCaixaLancamento.sessao_id == sessao_id)
            .order_by(FinCaixaLancamento.created_at.asc())
        )


class ContaReceberRepository(BaseRepository[FinContaReceber]):
    model = FinContaReceber

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FinContaReceber)
            .where(FinContaReceber.tenant_id == tenant_id, FinContaReceber.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: TituloStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        origem: ContaReceberOrigem | None = None,
    ) -> Select[tuple[FinContaReceber]]:
        stmt = self._base_query().order_by(FinContaReceber.vencimento.asc())
        if status:
            stmt = stmt.where(FinContaReceber.status == status)
        if cliente_id:
            stmt = stmt.where(FinContaReceber.cliente_id == cliente_id)
        if origem:
            stmt = stmt.where(FinContaReceber.origem == origem)
        return stmt


class ReceberBaixaRepository(BaseRepository[FinContaReceberBaixa]):
    model = FinContaReceberBaixa

    def list_by_titulo(self, titulo_id: uuid.UUID) -> Select[tuple[FinContaReceberBaixa]]:
        return (
            self._base_query()
            .where(FinContaReceberBaixa.titulo_id == titulo_id)
            .order_by(FinContaReceberBaixa.pago_em.asc())
        )


class ContaPagarRepository(BaseRepository[FinContaPagar]):
    model = FinContaPagar

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FinContaPagar)
            .where(FinContaPagar.tenant_id == tenant_id, FinContaPagar.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: TituloStatus | None = None,
        fornecedor_id: uuid.UUID | None = None,
        origem: ContaPagarOrigem | None = None,
    ) -> Select[tuple[FinContaPagar]]:
        stmt = self._base_query().order_by(FinContaPagar.vencimento.asc())
        if status:
            stmt = stmt.where(FinContaPagar.status == status)
        if fornecedor_id:
            stmt = stmt.where(FinContaPagar.fornecedor_id == fornecedor_id)
        if origem:
            stmt = stmt.where(FinContaPagar.origem == origem)
        return stmt


class PagarBaixaRepository(BaseRepository[FinContaPagarBaixa]):
    model = FinContaPagarBaixa

    def list_by_titulo(self, titulo_id: uuid.UUID) -> Select[tuple[FinContaPagarBaixa]]:
        return (
            self._base_query()
            .where(FinContaPagarBaixa.titulo_id == titulo_id)
            .order_by(FinContaPagarBaixa.pago_em.asc())
        )


class PixChaveRepository(BaseRepository[FinPixChave]):
    model = FinPixChave

    def list_query(self) -> Select[tuple[FinPixChave]]:
        return self._base_query().order_by(FinPixChave.created_at.desc())

    async def get_ativa(self, filial_id: uuid.UUID) -> FinPixChave | None:
        stmt = (
            self._base_query()
            .where(FinPixChave.filial_id == filial_id, FinPixChave.ativa.is_(True))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class PixCobrancaRepository(BaseRepository[FinPixCobranca]):
    model = FinPixCobranca

    def list_query(
        self, *, status: PixCobrancaStatus | None = None
    ) -> Select[tuple[FinPixCobranca]]:
        stmt = self._base_query().order_by(FinPixCobranca.created_at.desc())
        if status:
            stmt = stmt.where(FinPixCobranca.status == status)
        return stmt


class CartaoRepository(BaseRepository[FinCartaoTransacao]):
    model = FinCartaoTransacao

    def list_query(
        self, *, status: CartaoTransacaoStatus | None = None
    ) -> Select[tuple[FinCartaoTransacao]]:
        stmt = self._base_query().order_by(FinCartaoTransacao.created_at.desc())
        if status:
            stmt = stmt.where(FinCartaoTransacao.status == status)
        return stmt


class ContaBancariaRepository(BaseRepository[FinContaBancaria]):
    model = FinContaBancaria

    def list_query(self) -> Select[tuple[FinContaBancaria]]:
        return self._base_query().order_by(FinContaBancaria.banco_nome.asc())


class ExtratoLinhaRepository(BaseRepository[FinExtratoLinha]):
    model = FinExtratoLinha

    def list_query(
        self,
        *,
        conta_id: uuid.UUID | None = None,
        status: ConciliacaoStatus | None = None,
    ) -> Select[tuple[FinExtratoLinha]]:
        stmt = self._base_query().order_by(FinExtratoLinha.data_movimento.desc())
        if conta_id:
            stmt = stmt.where(FinExtratoLinha.conta_id == conta_id)
        if status:
            stmt = stmt.where(FinExtratoLinha.status_conciliacao == status)
        return stmt


class FaturamentoConfigRepository(BaseRepository[FinFaturamentoConfig]):
    model = FinFaturamentoConfig

    def list_query(self) -> Select[tuple[FinFaturamentoConfig]]:
        return self._base_query().order_by(FinFaturamentoConfig.created_at.desc())


class FaturaRepository(BaseRepository[FinFatura]):
    model = FinFatura

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FinFatura)
            .where(FinFatura.tenant_id == tenant_id, FinFatura.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(self, *, status: FaturaStatus | None = None) -> Select[tuple[FinFatura]]:
        stmt = self._base_query().order_by(FinFatura.created_at.desc())
        if status:
            stmt = stmt.where(FinFatura.status == status)
        return stmt


class FaturaTituloRepository(BaseRepository[FinFaturaTitulo]):
    model = FinFaturaTitulo

    def list_by_fatura(self, fatura_id: uuid.UUID) -> Select[tuple[FinFaturaTitulo]]:
        return self._base_query().where(FinFaturaTitulo.fatura_id == fatura_id)


# =========================================================== 9.1 Caixa
class CaixaService:
    """Gestão de sessões e lançamentos de caixa (§9.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CaixaSessaoRepository(session)
        self.lanc_repo = CaixaLancamentoRepository(session)

    async def list_sessoes(
        self,
        params: PageParams,
        *,
        status: CaixaSessaoStatus | None = None,
        filial_id: uuid.UUID | None = None,
    ) -> Page[FinCaixaSessao]:
        return await self.repo.paginate(
            params, stmt=self.repo.list_query(status=status, filial_id=filial_id)
        )

    async def get(self, sessao_id: uuid.UUID) -> FinCaixaSessao:
        item = await self.repo.get(sessao_id)
        if item is None:
            raise NotFoundError("Sessão de caixa não encontrada.")
        return item

    async def list_lancamentos(self, sessao_id: uuid.UUID) -> list[FinCaixaLancamento]:
        stmt = self.lanc_repo.list_by_sessao(sessao_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def abrir(
        self, tenant_id: uuid.UUID, data: CaixaAbrirInput, *, operador_id: uuid.UUID
    ) -> FinCaixaSessao:
        op_id = data.operador_id or operador_id
        existing = await self.repo.get_aberta(op_id, data.filial_id)
        if existing:
            raise ConflictError(
                "Operador já possui uma sessão de caixa aberta nesta filial.",
                code="caixa_ja_aberto",
            )
        sessao = FinCaixaSessao(
            tenant_id=tenant_id,
            filial_id=data.filial_id,
            operador_id=op_id,
            status=CaixaSessaoStatus.ABERTA,
            aberta_em=_now(),
            valor_abertura=_money(data.valor_abertura),
            observacoes=data.observacoes,
        )
        self.repo.add(sessao)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_caixa_sessao",
            entity_id=sessao.id,
            description=f"Caixa aberto (filial {data.filial_id}).",
        )
        return sessao

    async def registrar_lancamento(
        self,
        sessao_id: uuid.UUID,
        data: CaixaLancamentoCreate,
        *,
        created_by: uuid.UUID | None = None,
    ) -> FinCaixaLancamento:
        sessao = await self.get(sessao_id)
        if sessao.status != CaixaSessaoStatus.ABERTA:
            raise BusinessRuleError("Sessão de caixa fechada não aceita lançamentos.")
        lanc = FinCaixaLancamento(
            tenant_id=sessao.tenant_id,
            sessao_id=sessao.id,
            tipo=data.tipo,
            categoria=data.categoria,
            forma_pagamento=data.forma_pagamento,
            valor=_money(data.valor),
            descricao=data.descricao,
            referencia_tipo=data.referencia_tipo,
            referencia_id=data.referencia_id,
            created_by=created_by,
        )
        self.lanc_repo.add(lanc)
        await self.lanc_repo.flush()
        return lanc

    async def calcular_saldo(self, sessao_id: uuid.UUID) -> Decimal:
        sessao = await self.get(sessao_id)
        total = sessao.valor_abertura
        for lanc in await self.list_lancamentos(sessao_id):
            if lanc.tipo in _CREDIT_LANCAMENTOS:
                total += lanc.valor
            else:
                total -= lanc.valor
        return _money(total)

    async def fechar(self, sessao_id: uuid.UUID, data: CaixaFecharInput) -> FinCaixaSessao:
        sessao = await self.get(sessao_id)
        if sessao.status != CaixaSessaoStatus.ABERTA:
            raise BusinessRuleError("Sessão de caixa já está fechada.")
        calculado = await self.calcular_saldo(sessao_id)
        informado = _money(data.valor_fechamento_informado)
        sessao.valor_calculado = calculado
        sessao.valor_fechamento_informado = informado
        sessao.divergencia = _money(informado - calculado)
        sessao.status = CaixaSessaoStatus.FECHADA
        sessao.fechada_em = _now()
        if data.observacoes:
            sessao.observacoes = f"{sessao.observacoes or ''}\n{data.observacoes}".strip()
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_caixa_sessao",
            entity_id=sessao.id,
            description=f"Caixa fechado (divergência={sessao.divergencia}).",
        )
        return sessao


# =========================================================== 9.2 Contas a Receber
class ContaReceberService:
    """Gestão de títulos a receber (§9.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ContaReceberRepository(session)
        self.baixa_repo = ReceberBaixaRepository(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"CR-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: TituloStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        origem: ContaReceberOrigem | None = None,
    ) -> Page[FinContaReceber]:
        return await self.repo.paginate(
            params, stmt=self.repo.list_query(status=status, cliente_id=cliente_id, origem=origem)
        )

    async def get(self, titulo_id: uuid.UUID) -> FinContaReceber:
        item = await self.repo.get(titulo_id)
        if item is None:
            raise NotFoundError("Título a receber não encontrado.")
        return item

    async def list_baixas(self, titulo_id: uuid.UUID) -> list[FinContaReceberBaixa]:
        stmt = self.baixa_repo.list_by_titulo(titulo_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, tenant_id: uuid.UUID, data: ContaReceberCreate) -> FinContaReceber:
        valor = _money(data.valor_original)
        titulo = FinContaReceber(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            origem=data.origem,
            origem_id=data.origem_id,
            cliente_id=data.cliente_id,
            filial_id=data.filial_id,
            descricao=data.descricao,
            valor_original=valor,
            valor_pago=_ZERO,
            valor_saldo=valor,
            vencimento=data.vencimento,
            forma_prevista=data.forma_prevista,
            status=TituloStatus.EM_ABERTO,
            parcela_num=data.parcela_num,
            parcela_total=data.parcela_total,
            gera_pix=data.gera_pix,
            observacoes=data.observacoes,
        )
        self.repo.add(titulo)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_conta_receber",
            entity_id=titulo.id,
            description=f"Título a receber criado: {titulo.numero} ({valor}).",
        )
        return titulo

    async def from_origem(
        self,
        tenant_id: uuid.UUID,
        *,
        origem: ContaReceberOrigem,
        origem_id: uuid.UUID,
        cliente_id: uuid.UUID | None,
        filial_id: uuid.UUID,
        valor: Decimal,
        descricao: str,
        vencimento: date | None = None,
    ) -> FinContaReceber:
        """Cria um título a partir de outra entidade (contrato/multa/avaria/fatura)."""
        return await self.create(
            tenant_id,
            ContaReceberCreate(
                cliente_id=cliente_id,
                filial_id=filial_id,
                descricao=descricao,
                valor_original=_money(valor),
                vencimento=vencimento or (date.today() + timedelta(days=7)),
                origem=origem,
                origem_id=origem_id,
            ),
        )

    async def baixar(self, titulo_id: uuid.UUID, data: ReceberBaixaInput) -> FinContaReceber:
        titulo = await self.get(titulo_id)
        if titulo.status in _TITULO_TERMINAL:
            raise BusinessRuleError(
                f"Título {titulo.numero} não pode receber baixa (status {titulo.status.value})."
            )
        valor = _money(data.valor)
        if valor > titulo.valor_saldo:
            raise ValidationError("Valor da baixa excede o saldo do título.")

        caixa_lancamento_id: uuid.UUID | None = None
        if data.sessao_id:
            lanc = await CaixaService(self.session).registrar_lancamento(
                data.sessao_id,
                CaixaLancamentoCreate(
                    tipo=CaixaLancamentoTipo.ENTRADA,
                    valor=valor,
                    forma_pagamento=data.forma,
                    descricao=f"Recebimento {titulo.numero}",
                    referencia_tipo="conta_receber",
                    referencia_id=titulo.id,
                ),
            )
            caixa_lancamento_id = lanc.id

        baixa = FinContaReceberBaixa(
            tenant_id=titulo.tenant_id,
            titulo_id=titulo.id,
            valor=valor,
            forma=data.forma,
            pago_em=data.pago_em or _now(),
            caixa_lancamento_id=caixa_lancamento_id,
            observacao=data.observacao,
        )
        self.baixa_repo.add(baixa)
        await self.baixa_repo.flush()

        titulo.valor_pago = _money(titulo.valor_pago + valor)
        titulo.valor_saldo = _money(titulo.valor_original - titulo.valor_pago)
        titulo.status = TituloStatus.PAGO if titulo.valor_saldo <= _ZERO else TituloStatus.PAGO_PARCIAL
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_conta_receber",
            entity_id=titulo.id,
            description=f"Baixa de {valor} no título {titulo.numero} ({titulo.status.value}).",
        )
        return titulo

    async def estornar(self, titulo_id: uuid.UUID) -> FinContaReceber:
        titulo = await self.get(titulo_id)
        if titulo.status in {TituloStatus.CANCELADO, TituloStatus.ESTORNADO}:
            raise BusinessRuleError("Título já cancelado/estornado.")
        for baixa in await self.list_baixas(titulo_id):
            baixa.estornada = True
        titulo.valor_pago = _ZERO
        titulo.valor_saldo = titulo.valor_original
        titulo.status = TituloStatus.ESTORNADO
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_conta_receber",
            entity_id=titulo.id,
            description=f"Título estornado: {titulo.numero}.",
        )
        return titulo

    async def cancelar(self, titulo_id: uuid.UUID) -> FinContaReceber:
        titulo = await self.get(titulo_id)
        if titulo.valor_pago > _ZERO:
            raise BusinessRuleError("Título com baixas não pode ser cancelado; use estornar.")
        if titulo.status in {TituloStatus.CANCELADO, TituloStatus.ESTORNADO}:
            return titulo
        titulo.status = TituloStatus.CANCELADO
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_conta_receber",
            entity_id=titulo.id,
            description=f"Título cancelado: {titulo.numero}.",
        )
        return titulo

    async def marcar_vencidos(self, *, ref: date | None = None) -> int:
        ref = ref or date.today()
        stmt = self._base_open_query().where(
            FinContaReceber.vencimento < ref,
            FinContaReceber.status.in_({TituloStatus.EM_ABERTO, TituloStatus.PAGO_PARCIAL}),
            FinContaReceber.valor_saldo > _ZERO,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        for titulo in rows:
            titulo.status = TituloStatus.VENCIDO
        if rows:
            await self.repo.flush()
        return len(rows)

    def _base_open_query(self) -> Select[tuple[FinContaReceber]]:
        return select(FinContaReceber).where(FinContaReceber.deleted_at.is_(None))

    async def aging(self, *, ref: date | None = None) -> list[dict]:
        ref = ref or date.today()
        stmt = self._base_open_query().where(FinContaReceber.status.in_(_TITULO_ABERTO))
        rows = list((await self.session.execute(stmt)).scalars().all())
        buckets: dict[str, dict] = {b: {"bucket": b, "quantidade": 0, "total": _ZERO} for b in AGING_BUCKETS}
        for titulo in rows:
            key = aging_bucket(titulo.vencimento, ref)
            buckets[key]["quantidade"] += 1
            buckets[key]["total"] = _money(buckets[key]["total"] + titulo.valor_saldo)
        return [buckets[b] for b in AGING_BUCKETS]


# =========================================================== 9.3 Contas a Pagar
class ContaPagarService:
    """Gestão de títulos a pagar (§9.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ContaPagarRepository(session)
        self.baixa_repo = PagarBaixaRepository(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"CP-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: TituloStatus | None = None,
        fornecedor_id: uuid.UUID | None = None,
        origem: ContaPagarOrigem | None = None,
    ) -> Page[FinContaPagar]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(status=status, fornecedor_id=fornecedor_id, origem=origem),
        )

    async def get(self, titulo_id: uuid.UUID) -> FinContaPagar:
        item = await self.repo.get(titulo_id)
        if item is None:
            raise NotFoundError("Título a pagar não encontrado.")
        return item

    async def list_baixas(self, titulo_id: uuid.UUID) -> list[FinContaPagarBaixa]:
        stmt = self.baixa_repo.list_by_titulo(titulo_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, tenant_id: uuid.UUID, data: ContaPagarCreate) -> FinContaPagar:
        valor = _money(data.valor_original)
        titulo = FinContaPagar(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            origem=data.origem,
            origem_id=data.origem_id,
            fornecedor_id=data.fornecedor_id,
            beneficiario_nome=data.beneficiario_nome,
            filial_id=data.filial_id,
            descricao=data.descricao,
            valor_original=valor,
            valor_pago=_ZERO,
            valor_saldo=valor,
            vencimento=data.vencimento,
            forma_prevista=data.forma_prevista,
            status=TituloStatus.EM_ABERTO,
            pagamento_agendado_em=data.pagamento_agendado_em,
            nf_anexo_url=data.nf_anexo_url,
            observacoes=data.observacoes,
        )
        self.repo.add(titulo)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_conta_pagar",
            entity_id=titulo.id,
            description=f"Título a pagar criado: {titulo.numero} ({valor}).",
        )
        return titulo

    async def from_os(
        self,
        tenant_id: uuid.UUID,
        *,
        os_id: uuid.UUID,
        fornecedor_id: uuid.UUID | None,
        filial_id: uuid.UUID,
        valor: Decimal,
        descricao: str,
        vencimento: date | None = None,
    ) -> FinContaPagar:
        return await self.create(
            tenant_id,
            ContaPagarCreate(
                fornecedor_id=fornecedor_id,
                filial_id=filial_id,
                descricao=descricao,
                valor_original=_money(valor),
                vencimento=vencimento or (date.today() + timedelta(days=30)),
                origem=ContaPagarOrigem.OS,
                origem_id=os_id,
            ),
        )

    async def aprovar(self, titulo_id: uuid.UUID, data: PagarAprovarInput) -> FinContaPagar:
        titulo = await self.get(titulo_id)
        if titulo.status in _TITULO_TERMINAL:
            raise BusinessRuleError("Título em status terminal não pode ser aprovado.")
        titulo.aprovado_em = _now()
        titulo.aprovado_por = data.aprovado_por
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_conta_pagar",
            entity_id=titulo.id,
            description=f"Título a pagar aprovado: {titulo.numero}.",
        )
        return titulo

    async def efetivar_pagamento(
        self, titulo_id: uuid.UUID, data: PagarEfetivarInput
    ) -> FinContaPagar:
        titulo = await self.get(titulo_id)
        if titulo.aprovado_em is None:
            raise BusinessRuleError("Título deve ser aprovado antes do pagamento.")
        if titulo.status in _TITULO_TERMINAL:
            raise BusinessRuleError(
                f"Título {titulo.numero} não pode ser pago (status {titulo.status.value})."
            )
        valor = _money(data.valor)
        if valor > titulo.valor_saldo:
            raise ValidationError("Valor do pagamento excede o saldo do título.")

        caixa_lancamento_id: uuid.UUID | None = None
        if data.sessao_id:
            lanc = await CaixaService(self.session).registrar_lancamento(
                data.sessao_id,
                CaixaLancamentoCreate(
                    tipo=CaixaLancamentoTipo.SAIDA,
                    valor=valor,
                    forma_pagamento=data.forma,
                    descricao=f"Pagamento {titulo.numero}",
                    referencia_tipo="conta_pagar",
                    referencia_id=titulo.id,
                ),
            )
            caixa_lancamento_id = lanc.id

        baixa = FinContaPagarBaixa(
            tenant_id=titulo.tenant_id,
            titulo_id=titulo.id,
            valor=valor,
            forma=data.forma,
            pago_em=data.pago_em or _now(),
            caixa_lancamento_id=caixa_lancamento_id,
            conta_bancaria_id=data.conta_bancaria_id,
            observacao=data.observacao,
        )
        self.baixa_repo.add(baixa)
        await self.baixa_repo.flush()

        titulo.valor_pago = _money(titulo.valor_pago + valor)
        titulo.valor_saldo = _money(titulo.valor_original - titulo.valor_pago)
        titulo.status = TituloStatus.PAGO if titulo.valor_saldo <= _ZERO else TituloStatus.PAGO_PARCIAL

        if data.conta_bancaria_id:
            conta = await ContaBancariaRepository(self.session).get(data.conta_bancaria_id)
            if conta is not None:
                conta.saldo_atual = _money(conta.saldo_atual - valor)

        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_conta_pagar",
            entity_id=titulo.id,
            description=f"Pagamento de {valor} no título {titulo.numero} ({titulo.status.value}).",
        )
        return titulo

    async def cancelar(self, titulo_id: uuid.UUID) -> FinContaPagar:
        titulo = await self.get(titulo_id)
        if titulo.valor_pago > _ZERO:
            raise BusinessRuleError("Título com pagamentos não pode ser cancelado.")
        if titulo.status in {TituloStatus.CANCELADO, TituloStatus.ESTORNADO}:
            return titulo
        titulo.status = TituloStatus.CANCELADO
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_conta_pagar",
            entity_id=titulo.id,
            description=f"Título a pagar cancelado: {titulo.numero}.",
        )
        return titulo

    async def marcar_vencidos(self, *, ref: date | None = None) -> int:
        ref = ref or date.today()
        stmt = select(FinContaPagar).where(
            FinContaPagar.deleted_at.is_(None),
            FinContaPagar.vencimento < ref,
            FinContaPagar.status.in_({TituloStatus.EM_ABERTO, TituloStatus.PAGO_PARCIAL}),
            FinContaPagar.valor_saldo > _ZERO,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        for titulo in rows:
            titulo.status = TituloStatus.VENCIDO
        if rows:
            await self.repo.flush()
        return len(rows)


# =========================================================== 9.4 PIX
class PixService:
    """Gestão de chaves e cobranças PIX (§9.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chave_repo = PixChaveRepository(session)
        self.cobranca_repo = PixCobrancaRepository(session)

    async def list_chaves(self, params: PageParams) -> Page[FinPixChave]:
        return await self.chave_repo.paginate(params, stmt=self.chave_repo.list_query())

    async def list_cobrancas(
        self, params: PageParams, *, status: PixCobrancaStatus | None = None
    ) -> Page[FinPixCobranca]:
        return await self.cobranca_repo.paginate(
            params, stmt=self.cobranca_repo.list_query(status=status)
        )

    async def get_cobranca(self, cobranca_id: uuid.UUID) -> FinPixCobranca:
        item = await self.cobranca_repo.get(cobranca_id)
        if item is None:
            raise NotFoundError("Cobrança PIX não encontrada.")
        return item

    async def create_chave(self, tenant_id: uuid.UUID, data: PixChaveCreate) -> FinPixChave:
        chave = FinPixChave(
            tenant_id=tenant_id,
            filial_id=data.filial_id,
            conta_bancaria_id=data.conta_bancaria_id,
            tipo=data.tipo,
            chave=data.chave,
            ativa=data.ativa,
            descricao=data.descricao,
        )
        self.chave_repo.add(chave)
        await self.chave_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_pix_chave",
            entity_id=chave.id,
            description=f"Chave PIX cadastrada ({data.tipo.value}).",
        )
        return chave

    async def create_cobranca_from_titulo(
        self, data: PixCobrancaCreate
    ) -> FinPixCobranca:
        cr_svc = ContaReceberService(self.session)
        titulo = await cr_svc.get(data.titulo_receber_id)
        if titulo.status in _TITULO_TERMINAL:
            raise BusinessRuleError("Título não está aberto para cobrança PIX.")
        chave = await self.chave_repo.get_ativa(titulo.filial_id)
        txid = uuid.uuid4().hex[:32]
        payload = (
            f"00020126PIX-SIMULADO-{txid}520400005303986540"
            f"{titulo.valor_saldo}5802BR6009LOCADORA62070503***6304"
        )
        cobranca = FinPixCobranca(
            tenant_id=titulo.tenant_id,
            titulo_receber_id=titulo.id,
            chave_id=chave.id if chave else None,
            txid=txid,
            valor=titulo.valor_saldo,
            qr_code_payload=payload,
            status=PixCobrancaStatus.AGUARDANDO,
            expires_at=_now() + timedelta(minutes=data.expira_minutos),
        )
        self.cobranca_repo.add(cobranca)
        await self.cobranca_repo.flush()
        titulo.gera_pix = True
        await cr_svc.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_pix_cobranca",
            entity_id=cobranca.id,
            description=f"Cobrança PIX gerada para {titulo.numero} (txid={txid}).",
        )
        return cobranca

    async def confirmar_pagamento(self, cobranca_id: uuid.UUID) -> FinPixCobranca:
        cobranca = await self.get_cobranca(cobranca_id)
        if cobranca.status != PixCobrancaStatus.AGUARDANDO:
            raise BusinessRuleError("Cobrança PIX não está aguardando pagamento.")
        cobranca.status = PixCobrancaStatus.PAGO
        cobranca.pago_em = _now()
        await self.cobranca_repo.flush()

        if cobranca.titulo_receber_id:
            cr_svc = ContaReceberService(self.session)
            titulo = await cr_svc.get(cobranca.titulo_receber_id)
            if titulo.status not in _TITULO_TERMINAL and titulo.valor_saldo > _ZERO:
                await cr_svc.baixar(
                    titulo.id,
                    ReceberBaixaInput(
                        valor=titulo.valor_saldo,
                        forma=FormaPagamento.PIX,
                        observacao=f"PIX txid {cobranca.txid}",
                    ),
                )
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_pix_cobranca",
            entity_id=cobranca.id,
            description=f"Cobrança PIX confirmada (txid={cobranca.txid}).",
        )
        return cobranca

    async def expirar_vencidas(self, *, ref: datetime | None = None) -> int:
        ref = ref or _now()
        stmt = self.cobranca_repo.list_query(status=PixCobrancaStatus.AGUARDANDO).where(
            FinPixCobranca.expires_at.is_not(None),
            FinPixCobranca.expires_at < ref,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        for cobranca in rows:
            cobranca.status = PixCobrancaStatus.EXPIRADO
        if rows:
            await self.cobranca_repo.flush()
        return len(rows)


# =========================================================== 9.5 Cartões
class CartaoService:
    """Gestão de transações de cartão (§9.5)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CartaoRepository(session)

    async def list_items(
        self, params: PageParams, *, status: CartaoTransacaoStatus | None = None
    ) -> Page[FinCartaoTransacao]:
        return await self.repo.paginate(params, stmt=self.repo.list_query(status=status))

    async def get(self, transacao_id: uuid.UUID) -> FinCartaoTransacao:
        item = await self.repo.get(transacao_id)
        if item is None:
            raise NotFoundError("Transação de cartão não encontrada.")
        return item

    async def autorizar(
        self, tenant_id: uuid.UUID, data: CartaoAutorizarInput
    ) -> FinCartaoTransacao:
        transacao = FinCartaoTransacao(
            tenant_id=tenant_id,
            contrato_id=data.contrato_id,
            titulo_receber_id=data.titulo_receber_id,
            gateway=data.gateway,
            tipo=data.tipo,
            valor=_money(data.valor),
            parcelas=data.parcelas,
            status=CartaoTransacaoStatus.AUTORIZADO,
            taxa_adquirente=_money(data.taxa_adquirente),
            autorizacao_codigo=uuid.uuid4().hex[:10].upper(),
            observacoes=data.observacoes,
        )
        self.repo.add(transacao)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_cartao_transacao",
            entity_id=transacao.id,
            description=f"Cartão autorizado ({data.tipo.value}) valor {transacao.valor}.",
        )
        return transacao

    def _assert_cartao(self, atual: CartaoTransacaoStatus, novo: CartaoTransacaoStatus) -> None:
        if novo not in CARTAO_TRANSITIONS.get(atual, set()):
            raise BusinessRuleError(
                f"Transição de cartão inválida: {atual.value} → {novo.value}."
            )

    async def capturar(
        self, transacao_id: uuid.UUID, data: CartaoCapturarInput
    ) -> FinCartaoTransacao:
        transacao = await self.get(transacao_id)
        self._assert_cartao(transacao.status, CartaoTransacaoStatus.CAPTURADO)
        valor = _money(data.valor) if data.valor is not None else transacao.valor
        if valor > transacao.valor:
            raise ValidationError("Valor de captura excede o autorizado.")
        transacao.status = CartaoTransacaoStatus.CAPTURADO
        transacao.valor_capturado = valor
        transacao.capturado_em = _now()
        await self.repo.flush()

        if transacao.titulo_receber_id:
            cr_svc = ContaReceberService(self.session)
            titulo = await cr_svc.get(transacao.titulo_receber_id)
            if titulo.status not in _TITULO_TERMINAL and titulo.valor_saldo > _ZERO:
                baixa_valor = min(valor, titulo.valor_saldo)
                forma = (
                    FormaPagamento.CARTAO_DEBITO
                    if transacao.tipo == CartaoTipo.DEBITO
                    else FormaPagamento.CARTAO_CREDITO
                )
                await cr_svc.baixar(
                    titulo.id,
                    ReceberBaixaInput(valor=baixa_valor, forma=forma, observacao="Captura cartão"),
                )
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_cartao_transacao",
            entity_id=transacao.id,
            description=f"Cartão capturado valor {valor}.",
        )
        return transacao

    async def cancelar(self, transacao_id: uuid.UUID) -> FinCartaoTransacao:
        transacao = await self.get(transacao_id)
        self._assert_cartao(transacao.status, CartaoTransacaoStatus.CANCELADO)
        transacao.status = CartaoTransacaoStatus.CANCELADO
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_cartao_transacao",
            entity_id=transacao.id,
            description="Cartão cancelado.",
        )
        return transacao

    async def estornar(self, transacao_id: uuid.UUID) -> FinCartaoTransacao:
        transacao = await self.get(transacao_id)
        self._assert_cartao(transacao.status, CartaoTransacaoStatus.ESTORNADO)
        transacao.status = CartaoTransacaoStatus.ESTORNADO
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_cartao_transacao",
            entity_id=transacao.id,
            description="Cartão estornado.",
        )
        return transacao


# =========================================================== 9.6 Bancos
class BancoService:
    """Gestão de contas bancárias e extratos (§9.6)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ContaBancariaRepository(session)
        self.extrato_repo = ExtratoLinhaRepository(session)

    async def list_contas(self, params: PageParams) -> Page[FinContaBancaria]:
        return await self.repo.paginate(params, stmt=self.repo.list_query())

    async def get_conta(self, conta_id: uuid.UUID) -> FinContaBancaria:
        item = await self.repo.get(conta_id)
        if item is None:
            raise NotFoundError("Conta bancária não encontrada.")
        return item

    async def create_conta(
        self, tenant_id: uuid.UUID, data: ContaBancariaCreate
    ) -> FinContaBancaria:
        conta = FinContaBancaria(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(conta)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_conta_bancaria",
            entity_id=conta.id,
            description=f"Conta bancária criada: {conta.banco_nome} {conta.agencia}/{conta.conta}.",
        )
        return conta

    async def toggle_ativa(self, conta_id: uuid.UUID) -> FinContaBancaria:
        conta = await self.get_conta(conta_id)
        conta.ativa = not conta.ativa
        await self.repo.flush()
        return conta

    async def list_extrato(
        self,
        params: PageParams,
        *,
        conta_id: uuid.UUID | None = None,
        status: ConciliacaoStatus | None = None,
    ) -> Page[FinExtratoLinha]:
        return await self.extrato_repo.paginate(
            params, stmt=self.extrato_repo.list_query(conta_id=conta_id, status=status)
        )


# =========================================================== 9.7 Conciliação
class ConciliacaoService:
    """Importação de extratos e conciliação bancária (§9.7)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.extrato_repo = ExtratoLinhaRepository(session)
        self.banco_svc = BancoService(session)

    async def import_ofx_lines(self, tenant_id: uuid.UUID, data: OfxImportInput) -> int:
        """Importa linhas simples no formato ``data|valor|descricao|identificador``."""
        conta = await self.banco_svc.get_conta(data.conta_id)
        criadas = 0
        for raw in data.conteudo.splitlines():
            linha = raw.strip()
            if not linha or linha.startswith("#"):
                continue
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) < 3:
                continue
            try:
                data_mov = date.fromisoformat(partes[0])
                valor = Decimal(partes[1].replace(",", "."))
            except (ValueError, ArithmeticError):
                continue
            descricao = partes[2] or "Movimento"
            identificador = partes[3] if len(partes) > 3 else None
            tipo = ExtratoTipo.CREDITO if valor >= 0 else ExtratoTipo.DEBITO
            self.extrato_repo.add(
                FinExtratoLinha(
                    tenant_id=tenant_id,
                    conta_id=conta.id,
                    data_movimento=data_mov,
                    descricao=descricao,
                    valor=_money(abs(valor)),
                    tipo=tipo,
                    identificador_externo=identificador,
                    status_conciliacao=ConciliacaoStatus.PENDENTE,
                )
            )
            criadas += 1
        if criadas:
            await self.extrato_repo.flush()
        return criadas

    async def auto_match(self, conta_id: uuid.UUID, *, janela_dias: int = 2) -> int:
        """Concilia automaticamente por valor e proximidade de vencimento (± janela)."""
        stmt = self.extrato_repo.list_query(
            conta_id=conta_id, status=ConciliacaoStatus.PENDENTE
        )
        linhas = list((await self.session.execute(stmt)).scalars().all())
        conciliadas = 0
        cr_repo = ContaReceberRepository(self.session)
        cp_repo = ContaPagarRepository(self.session)
        for linha in linhas:
            delta = timedelta(days=janela_dias)
            inicio = linha.data_movimento - delta
            fim = linha.data_movimento + delta
            if linha.tipo == ExtratoTipo.CREDITO:
                q = cr_repo._base_query().where(
                    FinContaReceber.valor_original == linha.valor,
                    FinContaReceber.vencimento >= inicio,
                    FinContaReceber.vencimento <= fim,
                    FinContaReceber.status.in_(_TITULO_ABERTO | {TituloStatus.PAGO}),
                ).limit(1)
                match = (await self.session.execute(q)).scalar_one_or_none()
                titulo_tipo = "conta_receber"
            else:
                q = cp_repo._base_query().where(
                    FinContaPagar.valor_original == linha.valor,
                    FinContaPagar.vencimento >= inicio,
                    FinContaPagar.vencimento <= fim,
                    FinContaPagar.status.in_(_TITULO_ABERTO | {TituloStatus.PAGO}),
                ).limit(1)
                match = (await self.session.execute(q)).scalar_one_or_none()
                titulo_tipo = "conta_pagar"
            if match is not None:
                linha.status_conciliacao = ConciliacaoStatus.CONCILIADO
                linha.match_titulo_tipo = titulo_tipo
                linha.match_titulo_id = match.id
                conciliadas += 1
            else:
                linha.status_conciliacao = ConciliacaoStatus.DIVERGENTE
        if linhas:
            await self.extrato_repo.flush()
        return conciliadas

    async def manual_match(self, data: ManualMatchInput) -> FinExtratoLinha:
        linha = await self.extrato_repo.get(data.extrato_id)
        if linha is None:
            raise NotFoundError("Linha de extrato não encontrada.")
        linha.status_conciliacao = ConciliacaoStatus.CONCILIADO
        linha.match_titulo_tipo = data.titulo_tipo
        linha.match_titulo_id = data.titulo_id
        await self.extrato_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_extrato_linha",
            entity_id=linha.id,
            description=f"Conciliação manual com {data.titulo_tipo}.",
        )
        return linha

    async def list_divergencias(self, params: PageParams) -> Page[FinExtratoLinha]:
        stmt = self.extrato_repo.list_query(status=ConciliacaoStatus.DIVERGENTE)
        return await self.extrato_repo.paginate(params, stmt=stmt)


# =========================================================== 9.8 Faturamento
class FaturamentoService:
    """Faturamento consolidado por cliente (§9.8)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.config_repo = FaturamentoConfigRepository(session)
        self.fatura_repo = FaturaRepository(session)
        self.fatura_titulo_repo = FaturaTituloRepository(session)
        self.cr_svc = ContaReceberService(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.fatura_repo.count_by_tenant(tenant_id)
        return f"FAT-{count + 1:06d}"

    async def list_configs(self, params: PageParams) -> Page[FinFaturamentoConfig]:
        return await self.config_repo.paginate(params, stmt=self.config_repo.list_query())

    async def create_config(
        self, tenant_id: uuid.UUID, data: FaturamentoConfigCreate
    ) -> FinFaturamentoConfig:
        config = FinFaturamentoConfig(tenant_id=tenant_id, **data.model_dump())
        self.config_repo.add(config)
        await self.config_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_faturamento_config",
            entity_id=config.id,
            description=f"Config de faturamento criada ({data.ciclo.value}).",
        )
        return config

    async def list_faturas(
        self, params: PageParams, *, status: FaturaStatus | None = None
    ) -> Page[FinFatura]:
        return await self.fatura_repo.paginate(params, stmt=self.fatura_repo.list_query(status=status))

    async def get_fatura(self, fatura_id: uuid.UUID) -> FinFatura:
        item = await self.fatura_repo.get(fatura_id)
        if item is None:
            raise NotFoundError("Fatura não encontrada.")
        return item

    async def list_titulos(self, fatura_id: uuid.UUID) -> list[FinContaReceber]:
        stmt = self.fatura_titulo_repo.list_by_fatura(fatura_id)
        vinculos = list((await self.session.execute(stmt)).scalars().all())
        titulos: list[FinContaReceber] = []
        for vinc in vinculos:
            titulo = await self.cr_svc.repo.get(vinc.titulo_receber_id)
            if titulo is not None:
                titulos.append(titulo)
        return titulos

    async def consolidar(self, tenant_id: uuid.UUID, data: ConsolidarInput) -> FinFatura:
        stmt = self.cr_svc.repo._base_query().where(
            FinContaReceber.cliente_id == data.cliente_id,
            FinContaReceber.origem != ContaReceberOrigem.FATURA,
            FinContaReceber.status.in_(_TITULO_ABERTO),
            FinContaReceber.vencimento >= data.periodo_inicio,
            FinContaReceber.vencimento <= data.periodo_fim,
        )
        titulos = list((await self.session.execute(stmt)).scalars().all())
        if not titulos:
            raise BusinessRuleError("Nenhum título em aberto no período para consolidar.")

        total = _ZERO
        for titulo in titulos:
            total = _money(total + titulo.valor_saldo)

        fatura = FinFatura(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            cliente_id=data.cliente_id,
            periodo_inicio=data.periodo_inicio,
            periodo_fim=data.periodo_fim,
            valor_total=total,
            vencimento=data.vencimento or (data.periodo_fim + timedelta(days=10)),
            status=FaturaStatus.RASCUNHO,
        )
        self.fatura_repo.add(fatura)
        await self.fatura_repo.flush()

        for titulo in titulos:
            self.fatura_titulo_repo.add(
                FinFaturaTitulo(
                    tenant_id=tenant_id,
                    fatura_id=fatura.id,
                    titulo_receber_id=titulo.id,
                )
            )
        await self.fatura_titulo_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fin_fatura",
            entity_id=fatura.id,
            description=f"Fatura consolidada {fatura.numero} ({len(titulos)} títulos, {total}).",
        )
        return fatura

    async def emitir(self, fatura_id: uuid.UUID) -> FinFatura:
        fatura = await self.get_fatura(fatura_id)
        if fatura.status != FaturaStatus.RASCUNHO:
            raise BusinessRuleError("Somente faturas em rascunho podem ser emitidas.")

        titulos = await self.list_titulos(fatura_id)
        filial_id = titulos[0].filial_id if titulos else None
        if filial_id is None:
            raise BusinessRuleError("Fatura sem títulos vinculados não pode ser emitida.")

        cr = await self.cr_svc.from_origem(
            fatura.tenant_id,
            origem=ContaReceberOrigem.FATURA,
            origem_id=fatura.id,
            cliente_id=fatura.cliente_id,
            filial_id=filial_id,
            valor=fatura.valor_total,
            descricao=f"Fatura consolidada {fatura.numero}",
            vencimento=fatura.vencimento,
        )
        # Cancela os títulos individuais consolidados (substituídos pelo CR único).
        for titulo in titulos:
            if titulo.valor_pago <= _ZERO and titulo.status in _TITULO_ABERTO:
                titulo.status = TituloStatus.CANCELADO

        fatura.status = FaturaStatus.EMITIDA
        fatura.emitida_em = _now()
        fatura.conta_receber_id = cr.id
        await self.fatura_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fin_fatura",
            entity_id=fatura.id,
            description=f"Fatura emitida {fatura.numero} → título {cr.numero}.",
        )
        return fatura

    async def fechar_ciclos(self, tenant_id: uuid.UUID, *, ref: date | None = None) -> list[FinFatura]:
        """Job: consolida faturas para configs cujo dia de fechamento é hoje."""
        ref = ref or date.today()
        stmt = self.config_repo.list_query().where(FinFaturamentoConfig.ativo.is_(True))
        configs = list((await self.session.execute(stmt)).scalars().all())
        faturas: list[FinFatura] = []
        for config in configs:
            if config.dia_fechamento != ref.day:
                continue
            dias = 15 if config.ciclo.value == "quinzenal" else 30
            inicio = ref - timedelta(days=dias)
            try:
                fatura = await self.consolidar(
                    tenant_id,
                    ConsolidarInput(
                        cliente_id=config.cliente_id,
                        periodo_inicio=inicio,
                        periodo_fim=ref,
                    ),
                )
                faturas.append(fatura)
            except BusinessRuleError:
                continue
        return faturas
