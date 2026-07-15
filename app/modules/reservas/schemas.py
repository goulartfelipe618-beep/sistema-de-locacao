"""Schemas Pydantic do módulo Reservas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tarifario.schemas import AcessorioQuoteInput
from app.shared.enums import (
    CotacaoStatus,
    ReservaAlocacao,
    ReservaOrigem,
    ReservaStatus,
    TarifarioCanal,
)


class MotoristaReservaInput(BaseModel):
    motorista_id: uuid.UUID
    principal: bool = False


class ReservaCreate(BaseModel):
    """Dados do wizard de nova reserva (§5.1)."""

    cliente_id: uuid.UUID
    categoria_id: uuid.UUID
    filial_retirada_id: uuid.UUID
    filial_devolucao_id: uuid.UUID
    retirada_em: datetime
    devolucao_em: datetime
    origem: ReservaOrigem = ReservaOrigem.BALCAO
    veiculo_id: uuid.UUID | None = None
    endereco_entrega: str | None = None
    vendedor_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    politica_cancelamento_id: uuid.UUID | None = None
    forma_pagamento_prevista: str | None = Field(default=None, max_length=60)
    cupom_codigo: str | None = Field(default=None, max_length=40)
    protecao_ids: list[uuid.UUID] = Field(default_factory=list)
    taxa_ids: list[uuid.UUID] = Field(default_factory=list)
    acessorio_ids: list[AcessorioQuoteInput] = Field(default_factory=list)
    motoristas: list[MotoristaReservaInput] = Field(default_factory=list)
    observacoes: str | None = None
    desconto: Decimal = Field(default=Decimal("0"), ge=0)


class ReservaUpdate(BaseModel):
    """Atualização permitida enquanto PENDENTE."""

    categoria_id: uuid.UUID | None = None
    veiculo_id: uuid.UUID | None = None
    filial_retirada_id: uuid.UUID | None = None
    filial_devolucao_id: uuid.UUID | None = None
    retirada_em: datetime | None = None
    devolucao_em: datetime | None = None
    endereco_entrega: str | None = None
    vendedor_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    forma_pagamento_prevista: str | None = Field(default=None, max_length=60)
    cupom_codigo: str | None = Field(default=None, max_length=40)
    protecao_ids: list[uuid.UUID] | None = None
    taxa_ids: list[uuid.UUID] | None = None
    acessorio_ids: list[AcessorioQuoteInput] | None = None
    motoristas: list[MotoristaReservaInput] | None = None
    observacoes: str | None = None
    desconto: Decimal | None = Field(default=None, ge=0)


class ReservaCancelInput(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


class CotacaoCreate(BaseModel):
    """Parâmetros para cotação sem compromisso (§5.5)."""

    filial_retirada_id: uuid.UUID
    filial_devolucao_id: uuid.UUID
    categoria_id: uuid.UUID
    retirada_em: datetime
    devolucao_em: datetime
    origem: ReservaOrigem = ReservaOrigem.BALCAO
    canal: TarifarioCanal = TarifarioCanal.BALCAO
    cliente_id: uuid.UUID | None = None
    veiculo_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    protecao_ids: list[uuid.UUID] = Field(default_factory=list)
    taxa_ids: list[uuid.UUID] = Field(default_factory=list)
    acessorio_ids: list[AcessorioQuoteInput] = Field(default_factory=list)
    observacoes: str | None = None
    validade_horas: int = Field(default=24, ge=1, le=168)


class CotacaoConverterInput(BaseModel):
    """Dados adicionais ao converter cotação em reserva."""

    cliente_id: uuid.UUID
    motoristas: list[MotoristaReservaInput] = Field(default_factory=list)
    vendedor_id: uuid.UUID | None = None
    forma_pagamento_prevista: str | None = Field(default=None, max_length=60)
    politica_cancelamento_id: uuid.UUID | None = None
    observacoes: str | None = None


class CotacaoUpdate(BaseModel):
    """Atualização permitida enquanto ABERTA."""

    filial_retirada_id: uuid.UUID | None = None
    filial_devolucao_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    retirada_em: datetime | None = None
    devolucao_em: datetime | None = None
    origem: ReservaOrigem | None = None
    canal: TarifarioCanal | None = None
    cliente_id: uuid.UUID | None = None
    veiculo_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    protecao_ids: list[uuid.UUID] | None = None
    taxa_ids: list[uuid.UUID] | None = None
    acessorio_ids: list[AcessorioQuoteInput] | None = None
    observacoes: str | None = None
    validade_horas: int | None = Field(default=None, ge=1, le=168)


class CalendarioRealocarInput(BaseModel):
    reserva_id: uuid.UUID
    novo_veiculo_id: uuid.UUID


class DisponibilidadeVeiculo(BaseModel):
    id: uuid.UUID
    placa: str
    disponivel: bool


class DisponibilidadeCategoria(BaseModel):
    categoria_id: uuid.UUID
    nome: str
    total_frota: int
    ocupados: int
    livres: int
    veiculos: list[DisponibilidadeVeiculo]


class CalendarioEvento(BaseModel):
    reserva_id: uuid.UUID
    veiculo_id: uuid.UUID | None
    categoria_id: uuid.UUID
    start: datetime
    end: datetime
    status: ReservaStatus
    numero: str


class ReservaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    numero: str
    status: ReservaStatus
    alocacao: ReservaAlocacao
    origem: ReservaOrigem
    cliente_id: uuid.UUID
    categoria_id: uuid.UUID
    veiculo_id: uuid.UUID | None
    filial_retirada_id: uuid.UUID
    filial_devolucao_id: uuid.UUID
    retirada_em: datetime
    devolucao_em: datetime
    valor_total: Decimal
    requer_aprovacao: bool
    created_at: datetime


class CotacaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    numero: str
    status: CotacaoStatus
    validade_em: datetime
    categoria_id: uuid.UUID
    retirada_em: datetime
    devolucao_em: datetime
    valor_total: Decimal
    converted_reserva_id: uuid.UUID | None
    created_at: datetime
