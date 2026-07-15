"""Modelos ORM do módulo Financeiro (§9)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    BancoIntegracaoTipo,
    CaixaLancamentoTipo,
    CaixaSessaoStatus,
    CartaoTipo,
    CartaoTransacaoStatus,
    ConciliacaoStatus,
    ContaBancariaTipo,
    ContaPagarOrigem,
    ContaReceberOrigem,
    ExtratoTipo,
    FaturamentoCiclo,
    FaturaStatus,
    FormaPagamento,
    PixChaveTipo,
    PixCobrancaStatus,
    TituloStatus,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


# =========================================================== 9.1 Caixa
class FinCaixaSessao(TenantBaseModel):
    """Sessão de caixa aberta por um operador em uma filial (§9.1)."""

    __tablename__ = "fin_caixa_sessoes"
    __table_args__ = (
        Index("ix_fin_caixa_sessoes_tenant_status", "tenant_id", "status"),
        Index("ix_fin_caixa_sessoes_filial_id", "filial_id"),
        Index("ix_fin_caixa_sessoes_operador_id", "operador_id"),
    )

    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    operador_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[CaixaSessaoStatus] = mapped_column(
        _str_enum(CaixaSessaoStatus, "caixa_sessao_status", 10),
        nullable=False,
        default=CaixaSessaoStatus.ABERTA,
    )
    aberta_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fechada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valor_abertura: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_fechamento_informado: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    valor_calculado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    divergencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinCaixaLancamento(TenantBaseModel):
    """Lançamento (entrada/saída/sangria/suprimento) em uma sessão de caixa (§9.1)."""

    __tablename__ = "fin_caixa_lancamentos"
    __table_args__ = (
        Index("ix_fin_caixa_lancamentos_sessao_id", "sessao_id"),
        Index("ix_fin_caixa_lancamentos_tenant_tipo", "tenant_id", "tipo"),
    )

    sessao_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_caixa_sessoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[CaixaLancamentoTipo] = mapped_column(
        _str_enum(CaixaLancamentoTipo, "caixa_lancamento_tipo", 15),
        nullable=False,
    )
    categoria: Mapped[str | None] = mapped_column(String(80), nullable=True)
    forma_pagamento: Mapped[FormaPagamento] = mapped_column(
        _str_enum(FormaPagamento, "forma_pagamento", 20),
        nullable=False,
        default=FormaPagamento.DINHEIRO,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referencia_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


# =========================================================== 9.2 Contas a Receber
class FinContaReceber(TenantBaseModel):
    """Título a receber (§9.2)."""

    __tablename__ = "fin_contas_receber"
    __table_args__ = (
        Index(
            "uq_fin_contas_receber_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fin_contas_receber_tenant_status", "tenant_id", "status"),
        Index("ix_fin_contas_receber_cliente_id", "cliente_id"),
        Index("ix_fin_contas_receber_vencimento", "vencimento"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    origem: Mapped[ContaReceberOrigem] = mapped_column(
        _str_enum(ContaReceberOrigem, "conta_receber_origem", 15),
        nullable=False,
        default=ContaReceberOrigem.AVULSO,
    )
    origem_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    valor_original: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    valor_pago: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    forma_prevista: Mapped[FormaPagamento | None] = mapped_column(
        _str_enum(FormaPagamento, "forma_pagamento", 20),
        nullable=True,
    )
    status: Mapped[TituloStatus] = mapped_column(
        _str_enum(TituloStatus, "titulo_status", 15),
        nullable=False,
        default=TituloStatus.EM_ABERTO,
    )
    parcela_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parcela_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    gera_pix: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinContaReceberBaixa(TenantBaseModel):
    """Baixa (recebimento parcial/total) de um título a receber (§9.2)."""

    __tablename__ = "fin_receber_baixas"
    __table_args__ = (Index("ix_fin_receber_baixas_titulo_id", "titulo_id"),)

    titulo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_receber.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    forma: Mapped[FormaPagamento] = mapped_column(
        _str_enum(FormaPagamento, "forma_pagamento", 20),
        nullable=False,
        default=FormaPagamento.DINHEIRO,
    )
    pago_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    caixa_lancamento_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_caixa_lancamentos.id", ondelete="SET NULL"),
        nullable=True,
    )
    estornada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observacao: Mapped[str | None] = mapped_column(String(255), nullable=True)


# =========================================================== 9.3 Contas a Pagar
class FinContaPagar(TenantBaseModel):
    """Título a pagar (§9.3)."""

    __tablename__ = "fin_contas_pagar"
    __table_args__ = (
        Index(
            "uq_fin_contas_pagar_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fin_contas_pagar_tenant_status", "tenant_id", "status"),
        Index("ix_fin_contas_pagar_fornecedor_id", "fornecedor_id"),
        Index("ix_fin_contas_pagar_vencimento", "vencimento"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    origem: Mapped[ContaPagarOrigem] = mapped_column(
        _str_enum(ContaPagarOrigem, "conta_pagar_origem", 15),
        nullable=False,
        default=ContaPagarOrigem.AVULSO,
    )
    origem_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    beneficiario_nome: Mapped[str | None] = mapped_column(String(160), nullable=True)
    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    valor_original: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    valor_pago: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    forma_prevista: Mapped[FormaPagamento | None] = mapped_column(
        _str_enum(FormaPagamento, "forma_pagamento", 20),
        nullable=True,
    )
    status: Mapped[TituloStatus] = mapped_column(
        _str_enum(TituloStatus, "titulo_status", 15),
        nullable=False,
        default=TituloStatus.EM_ABERTO,
    )
    aprovado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aprovado_por: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pagamento_agendado_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    nf_anexo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinContaPagarBaixa(TenantBaseModel):
    """Baixa (pagamento parcial/total) de um título a pagar (§9.3)."""

    __tablename__ = "fin_pagar_baixas"
    __table_args__ = (Index("ix_fin_pagar_baixas_titulo_id", "titulo_id"),)

    titulo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_pagar.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    forma: Mapped[FormaPagamento] = mapped_column(
        _str_enum(FormaPagamento, "forma_pagamento", 20),
        nullable=False,
        default=FormaPagamento.DINHEIRO,
    )
    pago_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    caixa_lancamento_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_caixa_lancamentos.id", ondelete="SET NULL"),
        nullable=True,
    )
    conta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_bancarias.id", ondelete="SET NULL"),
        nullable=True,
    )
    observacao: Mapped[str | None] = mapped_column(String(255), nullable=True)


# =========================================================== 9.4 PIX
class FinPixChave(TenantBaseModel):
    """Chave PIX de recebimento (§9.4)."""

    __tablename__ = "fin_pix_chaves"
    __table_args__ = (
        Index("ix_fin_pix_chaves_tenant_ativa", "tenant_id", "ativa"),
        Index("ix_fin_pix_chaves_filial_id", "filial_id"),
    )

    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    conta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_bancarias.id", ondelete="SET NULL"),
        nullable=True,
    )
    tipo: Mapped[PixChaveTipo] = mapped_column(
        _str_enum(PixChaveTipo, "pix_chave_tipo", 12),
        nullable=False,
    )
    chave: Mapped[str] = mapped_column(String(140), nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)


class FinPixCobranca(TenantBaseModel):
    """Cobrança PIX vinculada a um título a receber (§9.4)."""

    __tablename__ = "fin_pix_cobrancas"
    __table_args__ = (
        Index("ix_fin_pix_cobrancas_titulo_id", "titulo_receber_id"),
        Index("ix_fin_pix_cobrancas_tenant_status", "tenant_id", "status"),
        Index(
            "uq_fin_pix_cobrancas_txid_active",
            "tenant_id",
            "txid",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    titulo_receber_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_receber.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chave_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_pix_chaves.id", ondelete="SET NULL"),
        nullable=True,
    )
    txid: Mapped[str] = mapped_column(String(40), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    qr_code_payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PixCobrancaStatus] = mapped_column(
        _str_enum(PixCobrancaStatus, "pix_cobranca_status", 12),
        nullable=False,
        default=PixCobrancaStatus.AGUARDANDO,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pago_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# =========================================================== 9.5 Cartões
class FinCartaoTransacao(TenantBaseModel):
    """Transação de cartão (débito/crédito/pré-autorização de caução) (§9.5)."""

    __tablename__ = "fin_cartao_transacoes"
    __table_args__ = (
        Index("ix_fin_cartao_transacoes_tenant_status", "tenant_id", "status"),
        Index("ix_fin_cartao_transacoes_contrato_id", "contrato_id"),
        Index("ix_fin_cartao_transacoes_titulo_id", "titulo_receber_id"),
    )

    contrato_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    titulo_receber_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_receber.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gateway: Mapped[str] = mapped_column(String(60), nullable=False, default="simulado")
    tipo: Mapped[CartaoTipo] = mapped_column(
        _str_enum(CartaoTipo, "cartao_tipo", 16),
        nullable=False,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    parcelas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[CartaoTransacaoStatus] = mapped_column(
        _str_enum(CartaoTransacaoStatus, "cartao_transacao_status", 16),
        nullable=False,
        default=CartaoTransacaoStatus.AUTORIZADO,
    )
    taxa_adquirente: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_capturado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    autorizacao_codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    capturado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


# =========================================================== 9.6 Bancos
class FinContaBancaria(TenantBaseModel):
    """Conta bancária da empresa/filial (§9.6)."""

    __tablename__ = "fin_contas_bancarias"
    __table_args__ = (
        Index("ix_fin_contas_bancarias_tenant_ativa", "tenant_id", "ativa"),
        Index("ix_fin_contas_bancarias_filial_id", "filial_id"),
    )

    banco_codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    banco_nome: Mapped[str] = mapped_column(String(120), nullable=False)
    agencia: Mapped[str] = mapped_column(String(20), nullable=False)
    conta: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo: Mapped[ContaBancariaTipo] = mapped_column(
        _str_enum(ContaBancariaTipo, "conta_bancaria_tipo", 12),
        nullable=False,
        default=ContaBancariaTipo.CORRENTE,
    )
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    saldo_atual: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    integracao_tipo: Mapped[BancoIntegracaoTipo] = mapped_column(
        _str_enum(BancoIntegracaoTipo, "banco_integracao_tipo", 10),
        nullable=False,
        default=BancoIntegracaoTipo.MANUAL,
    )


class FinExtratoLinha(TenantBaseModel):
    """Linha de extrato bancário para conciliação (§9.6/§9.7)."""

    __tablename__ = "fin_extrato_linhas"
    __table_args__ = (
        Index("ix_fin_extrato_linhas_conta_id", "conta_id"),
        Index("ix_fin_extrato_linhas_tenant_status", "tenant_id", "status_conciliacao"),
        Index("ix_fin_extrato_linhas_data_movimento", "data_movimento"),
    )

    conta_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_bancarias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_movimento: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tipo: Mapped[ExtratoTipo] = mapped_column(
        _str_enum(ExtratoTipo, "extrato_tipo", 1),
        nullable=False,
    )
    identificador_externo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status_conciliacao: Mapped[ConciliacaoStatus] = mapped_column(
        _str_enum(ConciliacaoStatus, "conciliacao_status", 12),
        nullable=False,
        default=ConciliacaoStatus.PENDENTE,
    )
    match_titulo_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    match_titulo_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)


# =========================================================== 9.8 Faturamento
class FinFaturamentoConfig(TenantBaseModel):
    """Configuração de faturamento consolidado por cliente (§9.8)."""

    __tablename__ = "fin_faturamento_configs"
    __table_args__ = (
        Index(
            "uq_fin_faturamento_configs_cliente_active",
            "tenant_id",
            "cliente_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ciclo: Mapped[FaturamentoCiclo] = mapped_column(
        _str_enum(FaturamentoCiclo, "faturamento_ciclo", 12),
        nullable=False,
        default=FaturamentoCiclo.MENSAL,
    )
    dia_fechamento: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FinFatura(TenantBaseModel):
    """Fatura consolidada de um cliente para um período (§9.8)."""

    __tablename__ = "fin_faturas"
    __table_args__ = (
        Index(
            "uq_fin_faturas_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fin_faturas_tenant_status", "tenant_id", "status"),
        Index("ix_fin_faturas_cliente_id", "cliente_id"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fim: Mapped[date] = mapped_column(Date, nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    emitida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vencimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[FaturaStatus] = mapped_column(
        _str_enum(FaturaStatus, "fatura_status", 12),
        nullable=False,
        default=FaturaStatus.RASCUNHO,
    )
    conta_receber_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_receber.id", ondelete="SET NULL"),
        nullable=True,
    )


class FinFaturaTitulo(TenantBaseModel):
    """Vínculo entre uma fatura e os títulos a receber consolidados (§9.8)."""

    __tablename__ = "fin_fatura_titulos"
    __table_args__ = (
        Index("ix_fin_fatura_titulos_fatura_id", "fatura_id"),
        Index(
            "uq_fin_fatura_titulos_active",
            "tenant_id",
            "fatura_id",
            "titulo_receber_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    fatura_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_faturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo_receber_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_receber.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
