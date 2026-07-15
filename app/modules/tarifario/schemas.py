"""Schemas Pydantic do módulo Tarifário."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    CadastroStatus,
    PoliticaRetencaoTipo,
    TarifarioCanal,
    TaxaAplicacao,
    TaxaCalculoTipo,
    TemporadaAjusteTipo,
)


# ------------------------------------------------------------------ Tabela de Tarifas
class TabelaItemCreate(BaseModel):
    categoria_id: uuid.UUID
    valor_1_3: Decimal = Field(default=Decimal("0"), ge=0)
    valor_4_7: Decimal = Field(default=Decimal("0"), ge=0)
    valor_8_15: Decimal = Field(default=Decimal("0"), ge=0)
    valor_16_30: Decimal = Field(default=Decimal("0"), ge=0)
    valor_mensal: Decimal = Field(default=Decimal("0"), ge=0)
    km_livre: bool = True
    km_incluido: int | None = Field(default=None, ge=0)
    valor_km_excedente: Decimal | None = Field(default=None, ge=0)


class TabelaItemUpdate(BaseModel):
    valor_1_3: Decimal | None = Field(default=None, ge=0)
    valor_4_7: Decimal | None = Field(default=None, ge=0)
    valor_8_15: Decimal | None = Field(default=None, ge=0)
    valor_16_30: Decimal | None = Field(default=None, ge=0)
    valor_mensal: Decimal | None = Field(default=None, ge=0)
    km_livre: bool | None = None
    km_incluido: int | None = Field(default=None, ge=0)
    valor_km_excedente: Decimal | None = Field(default=None, ge=0)


class TabelaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    vigencia_inicio: date
    vigencia_fim: date | None = None
    canal: TarifarioCanal = TarifarioCanal.TODOS
    filial_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    prioridade: int = Field(default=0, ge=0)
    status: CadastroStatus = CadastroStatus.ACTIVE
    observacoes: str | None = None
    itens: list[TabelaItemCreate] = Field(default_factory=list)


class TabelaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    canal: TarifarioCanal | None = None
    filial_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    prioridade: int | None = Field(default=None, ge=0)
    status: CadastroStatus | None = None
    observacoes: str | None = None


class TabelaItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tabela_id: uuid.UUID
    categoria_id: uuid.UUID
    valor_1_3: Decimal
    valor_4_7: Decimal
    valor_8_15: Decimal
    valor_16_30: Decimal
    valor_mensal: Decimal
    km_livre: bool
    km_incluido: int | None
    valor_km_excedente: Decimal | None


class TabelaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    vigencia_inicio: date
    vigencia_fim: date | None
    canal: TarifarioCanal
    filial_id: uuid.UUID | None
    parceiro_id: uuid.UUID | None
    cliente_id: uuid.UUID | None
    prioridade: int
    status: CadastroStatus
    observacoes: str | None
    created_at: datetime


# ------------------------------------------------------------------------ Temporada
class TemporadaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    data_inicio: date
    data_fim: date
    tipo_ajuste: TemporadaAjusteTipo
    valor_ajuste: Decimal = Field(default=Decimal("0"), ge=0)
    tabela_alternativa_id: uuid.UUID | None = None
    estadia_minima: int = Field(default=1, ge=1)
    prioridade: int = Field(default=0, ge=0)
    filial_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    status: CadastroStatus = CadastroStatus.ACTIVE


class TemporadaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    data_inicio: date | None = None
    data_fim: date | None = None
    tipo_ajuste: TemporadaAjusteTipo | None = None
    valor_ajuste: Decimal | None = Field(default=None, ge=0)
    tabela_alternativa_id: uuid.UUID | None = None
    estadia_minima: int | None = Field(default=None, ge=1)
    prioridade: int | None = Field(default=None, ge=0)
    filial_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    status: CadastroStatus | None = None


class TemporadaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    data_inicio: date
    data_fim: date
    tipo_ajuste: TemporadaAjusteTipo
    valor_ajuste: Decimal
    tabela_alternativa_id: uuid.UUID | None
    estadia_minima: int
    prioridade: int
    filial_id: uuid.UUID | None
    categoria_id: uuid.UUID | None
    status: CadastroStatus
    created_at: datetime


# --------------------------------------------------------------------------- Taxa
class TaxaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    descricao: str | None = None
    tipo_calculo: TaxaCalculoTipo
    valor: Decimal = Field(default=Decimal("0"), ge=0)
    aplicacao: TaxaAplicacao = TaxaAplicacao.OPCIONAL
    regra_codigo: str | None = Field(default=None, max_length=40)
    tributavel: bool = True
    status: CadastroStatus = CadastroStatus.ACTIVE


class TaxaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    descricao: str | None = None
    tipo_calculo: TaxaCalculoTipo | None = None
    valor: Decimal | None = Field(default=None, ge=0)
    aplicacao: TaxaAplicacao | None = None
    regra_codigo: str | None = Field(default=None, max_length=40)
    tributavel: bool | None = None
    status: CadastroStatus | None = None


class TaxaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    descricao: str | None
    tipo_calculo: TaxaCalculoTipo
    valor: Decimal
    aplicacao: TaxaAplicacao
    regra_codigo: str | None
    tributavel: bool
    status: CadastroStatus
    created_at: datetime


# ----------------------------------------------------------------------- Proteção
class ProtecaoCategoriaLink(BaseModel):
    categoria_id: uuid.UUID


class ProtecaoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    descricao: str | None = None
    valor_diaria: Decimal = Field(default=Decimal("0"), ge=0)
    franquia: Decimal = Field(default=Decimal("0"), ge=0)
    fornecedor_id: uuid.UUID | None = None
    exclusoes: str | None = None
    obrigatoria: bool = False
    status: CadastroStatus = CadastroStatus.ACTIVE
    categorias_obrigatorias: list[uuid.UUID] = Field(default_factory=list)


class ProtecaoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    descricao: str | None = None
    valor_diaria: Decimal | None = Field(default=None, ge=0)
    franquia: Decimal | None = Field(default=None, ge=0)
    fornecedor_id: uuid.UUID | None = None
    exclusoes: str | None = None
    obrigatoria: bool | None = None
    status: CadastroStatus | None = None
    categorias_obrigatorias: list[uuid.UUID] | None = None


class ProtecaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    descricao: str | None
    valor_diaria: Decimal
    franquia: Decimal
    fornecedor_id: uuid.UUID | None
    exclusoes: str | None
    obrigatoria: bool
    status: CadastroStatus
    created_at: datetime


# ---------------------------------------------------------- Política Cancelamento
class PoliticaFaixaCreate(BaseModel):
    horas_antes_min: int = Field(default=0, ge=0)
    horas_antes_max: int | None = Field(default=None, ge=0)
    tipo_retencao: PoliticaRetencaoTipo
    valor_retencao: Decimal = Field(default=Decimal("0"), ge=0)
    ordem: int = Field(default=0, ge=0)


class PoliticaFaixaUpdate(BaseModel):
    horas_antes_min: int | None = Field(default=None, ge=0)
    horas_antes_max: int | None = Field(default=None, ge=0)
    tipo_retencao: PoliticaRetencaoTipo | None = None
    valor_retencao: Decimal | None = Field(default=None, ge=0)
    ordem: int | None = Field(default=None, ge=0)


class PoliticaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    canal: TarifarioCanal = TarifarioCanal.TODOS
    status: CadastroStatus = CadastroStatus.ACTIVE
    descricao: str | None = None
    faixas: list[PoliticaFaixaCreate] = Field(default_factory=list)


class PoliticaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    canal: TarifarioCanal | None = None
    status: CadastroStatus | None = None
    descricao: str | None = None


class PoliticaFaixaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    politica_id: uuid.UUID
    horas_antes_min: int
    horas_antes_max: int | None
    tipo_retencao: PoliticaRetencaoTipo
    valor_retencao: Decimal
    ordem: int


class PoliticaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    canal: TarifarioCanal
    status: CadastroStatus
    descricao: str | None
    created_at: datetime


# ----------------------------------------------------------------------- Pricing
class AcessorioQuoteInput(BaseModel):
    id: uuid.UUID
    qtd: int = Field(default=1, ge=1)


class PricingQuoteInput(BaseModel):
    tenant_id: uuid.UUID
    filial_id: uuid.UUID
    categoria_id: uuid.UUID
    canal: TarifarioCanal
    retirada_em: datetime
    devolucao_em: datetime
    veiculo_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    protecao_ids: list[uuid.UUID] = Field(default_factory=list)
    taxa_ids: list[uuid.UUID] = Field(default_factory=list)
    acessorio_ids: list[AcessorioQuoteInput] = Field(default_factory=list)
    one_way: bool = False


class PricingLineItem(BaseModel):
    tipo: str
    referencia_id: uuid.UUID | None = None
    nome: str
    quantidade: Decimal = Decimal("1")
    valor_unitario: Decimal
    valor_total: Decimal
    automatica: bool = False


class PricingQuoteResult(BaseModel):
    diaria_unitaria: Decimal
    dias: int
    dias_cobrados: int
    subtotal_diarias: Decimal
    temporada_id: uuid.UUID | None = None
    temporada_nome: str | None = None
    temporada_ajuste: Decimal
    estadia_minima: int = 1
    taxas: list[PricingLineItem]
    protecoes: list[PricingLineItem]
    acessorios: list[PricingLineItem]
    subtotal_taxas: Decimal
    subtotal_protecoes: Decimal
    subtotal_acessorios: Decimal
    total: Decimal
    tabela_id: uuid.UUID
    tabela_nome: str
    politica_sugerida_id: uuid.UUID | None = None
    km_livre: bool = True
    km_incluido: int | None = None
    valor_km_excedente: Decimal | None = None
    breakdown: dict
    snapshot: dict


class CancelamentoSimulacao(BaseModel):
    politica_id: uuid.UUID
    faixa_id: uuid.UUID | None = None
    horas_antes_retirada: int
    valor_reserva: Decimal
    valor_retencao: Decimal
    valor_estorno: Decimal
    tipo_retencao: PoliticaRetencaoTipo | None = None
    descricao_faixa: str | None = None


class PricingQuoteRequest(BaseModel):
    filial_id: uuid.UUID
    categoria_id: uuid.UUID
    canal: TarifarioCanal
    retirada_em: datetime
    devolucao_em: datetime
    veiculo_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    protecao_ids: list[uuid.UUID] = Field(default_factory=list)
    taxa_ids: list[uuid.UUID] = Field(default_factory=list)
    acessorio_ids: list[AcessorioQuoteInput] = Field(default_factory=list)
    one_way: bool = False


class CancelamentoSimulacaoRequest(BaseModel):
    politica_id: uuid.UUID
    valor_reserva: Decimal = Field(gt=0)
    horas_antes_retirada: int = Field(ge=0)
    diaria_unitaria: Decimal | None = Field(default=None, ge=0)
    dias_locacao: int = Field(default=1, ge=1)


class ProtecaoCategoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    protecao_id: uuid.UUID
    categoria_id: uuid.UUID
