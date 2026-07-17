"""Schemas Pydantic — módulo Intermediação."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    ContratoFornecedorStatus,
    IndisponibilidadeTerceiroMotivo,
    IntermediacaoStatus,
    ModeloNegocioTerceiro,
    ModoOperacaoLocadora,
    TituloStatus,
    TipoCalculoRepasse,
)


class IntermediacaoConfigRead(BaseModel):
    modo_operacao: ModoOperacaoLocadora
    exige_contrato_fornecedor: bool
    aprovar_reserva_automaticamente: bool
    publicar_terceiros_site: bool
    margem_minima_percentual: Decimal
    buffer_disponibilidade_horas: int
    priorizar_frota_propria: bool
    observacoes: str | None = None


class IntermediacaoConfigUpdate(BaseModel):
    modo_operacao: ModoOperacaoLocadora | None = None
    exige_contrato_fornecedor: bool | None = None
    aprovar_reserva_automaticamente: bool | None = None
    publicar_terceiros_site: bool | None = None
    margem_minima_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    buffer_disponibilidade_horas: int | None = Field(default=None, ge=0, le=72)
    priorizar_frota_propria: bool | None = None
    observacoes: str | None = None


class ContratoFornecedorCreate(BaseModel):
    fornecedor_id: uuid.UUID
    numero: str = Field(min_length=1, max_length=30)
    titulo: str = Field(min_length=2, max_length=200)
    modelo_negocio: ModeloNegocioTerceiro = ModeloNegocioTerceiro.REPASSE
    tipo_calculo: TipoCalculoRepasse = TipoCalculoRepasse.PERCENTUAL_RECEITA
    percentual_repasse: Decimal | None = Field(default=None, ge=0, le=100)
    percentual_comissao: Decimal | None = Field(default=None, ge=0, le=100)
    valor_diaria_repasse: Decimal | None = Field(default=None, ge=0)
    margem_minima_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    prazo_pagamento_dias: int = Field(default=30, ge=0, le=365)
    vigencia_inicio: date
    vigencia_fim: date | None = None
    km_livre_dia: int | None = Field(default=None, ge=0)
    valor_km_excedente: Decimal | None = Field(default=None, ge=0)
    seguro_incluso: bool = False
    clausulas: str | None = None
    observacoes: str | None = None


class ContratoFornecedorUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=2, max_length=200)
    status: ContratoFornecedorStatus | None = None
    modelo_negocio: ModeloNegocioTerceiro | None = None
    tipo_calculo: TipoCalculoRepasse | None = None
    percentual_repasse: Decimal | None = Field(default=None, ge=0, le=100)
    percentual_comissao: Decimal | None = Field(default=None, ge=0, le=100)
    valor_diaria_repasse: Decimal | None = Field(default=None, ge=0)
    margem_minima_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    prazo_pagamento_dias: int | None = Field(default=None, ge=0, le=365)
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    km_livre_dia: int | None = Field(default=None, ge=0)
    valor_km_excedente: Decimal | None = Field(default=None, ge=0)
    seguro_incluso: bool | None = None
    clausulas: str | None = None
    observacoes: str | None = None


class ContratoPrecoCreate(BaseModel):
    categoria_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    vigencia_inicio: date
    vigencia_fim: date | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    dias_minimos: int = Field(default=1, ge=1)
    dias_maximos: int | None = Field(default=None, ge=1)
    valor_cliente_diaria: Decimal = Field(ge=0)
    valor_repasse_diaria: Decimal = Field(ge=0)
    valor_hora_extra_cliente: Decimal | None = Field(default=None, ge=0)
    valor_hora_extra_repasse: Decimal | None = Field(default=None, ge=0)
    percentual_comissao: Decimal | None = Field(default=None, ge=0, le=100)
    taxa_entrega: Decimal | None = Field(default=None, ge=0)
    prioridade: int = 0
    observacoes: str | None = None


class IndisponibilidadeTerceiroCreate(BaseModel):
    veiculo_id: uuid.UUID
    fornecedor_id: uuid.UUID
    inicio_em: datetime
    fim_em: datetime | None = None
    motivo: IndisponibilidadeTerceiroMotivo = IndisponibilidadeTerceiroMotivo.LOCADO_PELO_PROPRIETARIO
    sincronizar_site: bool = True
    observacoes: str | None = None


class RepasseCalculoResult(BaseModel):
    modelo_negocio: ModeloNegocioTerceiro
    valor_cliente: Decimal
    valor_repasse: Decimal
    valor_margem: Decimal
    valor_comissao: Decimal
    margem_percentual: Decimal
    contrato_fornecedor_id: uuid.UUID | None = None
    fornecedor_id: uuid.UUID | None = None
    snapshot: dict


class ContratoFornecedorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fornecedor_id: uuid.UUID
    numero: str
    titulo: str
    status: ContratoFornecedorStatus
    modelo_negocio: ModeloNegocioTerceiro
    tipo_calculo: TipoCalculoRepasse
    vigencia_inicio: date
    vigencia_fim: date | None = None
    prazo_pagamento_dias: int


class RepasseLancamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contrato_id: uuid.UUID
    reserva_id: uuid.UUID | None
    fornecedor_id: uuid.UUID
    modelo_negocio: ModeloNegocioTerceiro
    valor_cliente: Decimal
    valor_repasse: Decimal
    valor_margem: Decimal
    valor_comissao: Decimal
    status: TituloStatus
    vencimento: date


class AprovacaoPendenteRead(BaseModel):
    id: uuid.UUID
    numero: str
    cliente_id: uuid.UUID
    fornecedor_id: uuid.UUID | None
    retirada_em: datetime
    valor_total: Decimal
    valor_repasse_total: Decimal | None
    intermediacao_status: IntermediacaoStatus


class RejeitarFornecedorInput(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)
