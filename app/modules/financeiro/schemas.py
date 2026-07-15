"""Schemas Pydantic do módulo Financeiro (§9)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

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


# ============================================================ 9.1 Caixa
class CaixaAbrirInput(BaseModel):
    filial_id: uuid.UUID
    operador_id: uuid.UUID | None = None
    valor_abertura: Decimal = Field(default=Decimal("0"), ge=0)
    observacoes: str | None = None


class CaixaLancamentoCreate(BaseModel):
    tipo: CaixaLancamentoTipo
    valor: Decimal = Field(gt=0)
    forma_pagamento: FormaPagamento = FormaPagamento.DINHEIRO
    categoria: str | None = Field(default=None, max_length=80)
    descricao: str | None = Field(default=None, max_length=255)
    referencia_tipo: str | None = Field(default=None, max_length=40)
    referencia_id: uuid.UUID | None = None


class CaixaFecharInput(BaseModel):
    valor_fechamento_informado: Decimal = Field(ge=0)
    observacoes: str | None = None


class CaixaSessaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filial_id: uuid.UUID
    operador_id: uuid.UUID
    status: CaixaSessaoStatus
    aberta_em: datetime
    fechada_em: datetime | None
    valor_abertura: Decimal
    valor_fechamento_informado: Decimal | None
    valor_calculado: Decimal | None
    divergencia: Decimal | None


class CaixaLancamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sessao_id: uuid.UUID
    tipo: CaixaLancamentoTipo
    forma_pagamento: FormaPagamento
    valor: Decimal
    descricao: str | None
    created_at: datetime


# ============================================================ 9.2 Contas a Receber
class ContaReceberCreate(BaseModel):
    cliente_id: uuid.UUID | None = None
    filial_id: uuid.UUID
    descricao: str = Field(min_length=1, max_length=255)
    valor_original: Decimal = Field(gt=0)
    vencimento: date
    origem: ContaReceberOrigem = ContaReceberOrigem.AVULSO
    origem_id: uuid.UUID | None = None
    forma_prevista: FormaPagamento | None = None
    parcela_num: int = Field(default=1, ge=1)
    parcela_total: int = Field(default=1, ge=1)
    gera_pix: bool = False
    observacoes: str | None = None


class ReceberBaixaInput(BaseModel):
    valor: Decimal = Field(gt=0)
    forma: FormaPagamento = FormaPagamento.DINHEIRO
    pago_em: datetime | None = None
    sessao_id: uuid.UUID | None = None
    observacao: str | None = Field(default=None, max_length=255)


class ContaReceberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    origem: ContaReceberOrigem
    cliente_id: uuid.UUID | None
    filial_id: uuid.UUID
    descricao: str
    valor_original: Decimal
    valor_pago: Decimal
    valor_saldo: Decimal
    vencimento: date
    status: TituloStatus
    gera_pix: bool
    created_at: datetime


class AgingBucket(BaseModel):
    bucket: str
    quantidade: int
    total: Decimal


# ============================================================ 9.3 Contas a Pagar
class ContaPagarCreate(BaseModel):
    fornecedor_id: uuid.UUID | None = None
    beneficiario_nome: str | None = Field(default=None, max_length=160)
    filial_id: uuid.UUID
    descricao: str = Field(min_length=1, max_length=255)
    valor_original: Decimal = Field(gt=0)
    vencimento: date
    origem: ContaPagarOrigem = ContaPagarOrigem.AVULSO
    origem_id: uuid.UUID | None = None
    forma_prevista: FormaPagamento | None = None
    pagamento_agendado_em: date | None = None
    nf_anexo_url: str | None = Field(default=None, max_length=500)
    observacoes: str | None = None


class PagarAprovarInput(BaseModel):
    aprovado_por: uuid.UUID | None = None


class PagarEfetivarInput(BaseModel):
    valor: Decimal = Field(gt=0)
    forma: FormaPagamento = FormaPagamento.TRANSFERENCIA
    pago_em: datetime | None = None
    conta_bancaria_id: uuid.UUID | None = None
    sessao_id: uuid.UUID | None = None
    observacao: str | None = Field(default=None, max_length=255)


class ContaPagarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    origem: ContaPagarOrigem
    fornecedor_id: uuid.UUID | None
    beneficiario_nome: str | None
    filial_id: uuid.UUID
    descricao: str
    valor_original: Decimal
    valor_pago: Decimal
    valor_saldo: Decimal
    vencimento: date
    status: TituloStatus
    aprovado_em: datetime | None
    created_at: datetime


# ============================================================ 9.4 PIX
class PixChaveCreate(BaseModel):
    filial_id: uuid.UUID
    tipo: PixChaveTipo
    chave: str = Field(min_length=1, max_length=140)
    conta_bancaria_id: uuid.UUID | None = None
    descricao: str | None = Field(default=None, max_length=200)
    ativa: bool = True


class PixChaveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filial_id: uuid.UUID
    tipo: PixChaveTipo
    chave: str
    ativa: bool
    descricao: str | None


class PixCobrancaCreate(BaseModel):
    titulo_receber_id: uuid.UUID
    expira_minutos: int = Field(default=60, ge=1, le=1440)


class PixCobrancaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo_receber_id: uuid.UUID | None
    txid: str
    valor: Decimal
    qr_code_payload: str
    status: PixCobrancaStatus
    expires_at: datetime | None
    pago_em: datetime | None


# ============================================================ 9.5 Cartões
class CartaoAutorizarInput(BaseModel):
    tipo: CartaoTipo
    valor: Decimal = Field(gt=0)
    parcelas: int = Field(default=1, ge=1, le=24)
    contrato_id: uuid.UUID | None = None
    titulo_receber_id: uuid.UUID | None = None
    gateway: str = Field(default="simulado", max_length=60)
    taxa_adquirente: Decimal = Field(default=Decimal("0"), ge=0)
    observacoes: str | None = None


class CartaoCapturarInput(BaseModel):
    valor: Decimal | None = Field(default=None, gt=0)


class CartaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contrato_id: uuid.UUID | None
    titulo_receber_id: uuid.UUID | None
    tipo: CartaoTipo
    valor: Decimal
    valor_capturado: Decimal
    parcelas: int
    status: CartaoTransacaoStatus
    taxa_adquirente: Decimal
    autorizacao_codigo: str | None
    capturado_em: datetime | None


# ============================================================ 9.6 Bancos
class ContaBancariaCreate(BaseModel):
    banco_codigo: str = Field(min_length=1, max_length=10)
    banco_nome: str = Field(min_length=1, max_length=120)
    agencia: str = Field(min_length=1, max_length=20)
    conta: str = Field(min_length=1, max_length=30)
    tipo: ContaBancariaTipo = ContaBancariaTipo.CORRENTE
    filial_id: uuid.UUID | None = None
    saldo_atual: Decimal = Field(default=Decimal("0"))
    integracao_tipo: BancoIntegracaoTipo = BancoIntegracaoTipo.MANUAL
    ativa: bool = True


class ContaBancariaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    banco_codigo: str
    banco_nome: str
    agencia: str
    conta: str
    tipo: ContaBancariaTipo
    filial_id: uuid.UUID | None
    saldo_atual: Decimal
    ativa: bool
    integracao_tipo: BancoIntegracaoTipo


class ExtratoLinhaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conta_id: uuid.UUID
    data_movimento: date
    descricao: str
    valor: Decimal
    tipo: ExtratoTipo
    status_conciliacao: ConciliacaoStatus
    match_titulo_tipo: str | None
    match_titulo_id: uuid.UUID | None


# ============================================================ 9.7 Conciliação
class OfxImportInput(BaseModel):
    conta_id: uuid.UUID
    conteudo: str = Field(min_length=1)


class ManualMatchInput(BaseModel):
    extrato_id: uuid.UUID
    titulo_tipo: str = Field(min_length=1, max_length=20)
    titulo_id: uuid.UUID


# ============================================================ 9.8 Faturamento
class FaturamentoConfigCreate(BaseModel):
    cliente_id: uuid.UUID
    ciclo: FaturamentoCiclo = FaturamentoCiclo.MENSAL
    dia_fechamento: int = Field(default=1, ge=1, le=28)
    ativo: bool = True


class FaturamentoConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_id: uuid.UUID
    ciclo: FaturamentoCiclo
    dia_fechamento: int
    ativo: bool


class ConsolidarInput(BaseModel):
    cliente_id: uuid.UUID
    periodo_inicio: date
    periodo_fim: date
    vencimento: date | None = None


class FaturaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    cliente_id: uuid.UUID
    periodo_inicio: date
    periodo_fim: date
    valor_total: Decimal
    emitida_em: datetime | None
    vencimento: date | None
    status: FaturaStatus
