"""Schemas Pydantic do módulo Locações."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tarifario.schemas import AcessorioQuoteInput
from app.shared.enums import (
    AvariaOrigem,
    AvariaResponsabilidade,
    AvariaSeveridade,
    AvariaStatus,
    ContratoCondicaoPagamento,
    ContratoStatus,
    MultaStatus,
    ReservaOrigem,
    VistoriaTipo,
)


class MotoristaContratoInput(BaseModel):
    motorista_id: uuid.UUID
    principal: bool = False


class ContratoCreate(BaseModel):
    """Criação de contrato no balcão (sem reserva prévia)."""

    cliente_id: uuid.UUID
    veiculo_id: uuid.UUID
    categoria_id: uuid.UUID
    filial_retirada_id: uuid.UUID
    filial_devolucao_id: uuid.UUID
    retirada_prevista_em: datetime
    devolucao_prevista_em: datetime
    origem: ReservaOrigem = ReservaOrigem.BALCAO
    parceiro_id: uuid.UUID | None = None
    forma_pagamento: str | None = Field(default=None, max_length=60)
    condicao: ContratoCondicaoPagamento = ContratoCondicaoPagamento.AVISTA
    caucao: Decimal = Field(default=Decimal("0"), ge=0)
    protecao_ids: list[uuid.UUID] = Field(default_factory=list)
    taxa_ids: list[uuid.UUID] = Field(default_factory=list)
    acessorio_ids: list[AcessorioQuoteInput] = Field(default_factory=list)
    motoristas: list[MotoristaContratoInput] = Field(default_factory=list)
    desconto: Decimal = Field(default=Decimal("0"), ge=0)
    clausulas_combustivel: str | None = None
    observacoes: str | None = None


class ContratoUpdate(BaseModel):
    """Atualização permitida enquanto RASCUNHO."""

    filial_retirada_id: uuid.UUID | None = None
    filial_devolucao_id: uuid.UUID | None = None
    retirada_prevista_em: datetime | None = None
    devolucao_prevista_em: datetime | None = None
    forma_pagamento: str | None = Field(default=None, max_length=60)
    condicao: ContratoCondicaoPagamento | None = None
    caucao: Decimal | None = Field(default=None, ge=0)
    protecao_ids: list[uuid.UUID] | None = None
    taxa_ids: list[uuid.UUID] | None = None
    acessorio_ids: list[AcessorioQuoteInput] | None = None
    motoristas: list[MotoristaContratoInput] | None = None
    desconto: Decimal | None = Field(default=None, ge=0)
    clausulas_combustivel: str | None = None
    observacoes: str | None = None


class ContratoCancelInput(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


class VistoriaFotoInput(BaseModel):
    storage_key: str = Field(min_length=1, max_length=500)
    angulo: str = Field(min_length=1, max_length=30)
    ordem: int = Field(default=0, ge=0)


class CheckoutConcluirInput(BaseModel):
    """Payload de conclusão do check-out."""

    km: int = Field(ge=0)
    combustivel_nivel: int = Field(ge=0, le=8)
    checklist_json: dict = Field(default_factory=dict)
    fotos: list[VistoriaFotoInput] = Field(default_factory=list)
    caucao_confirmada: bool = False
    allow_force: bool = False
    realizado_em: datetime | None = None
    realizado_por_user_id: uuid.UUID | None = None
    assinatura_tipo: str | None = Field(default=None, max_length=20)
    assinatura_key: str | None = Field(default=None, max_length=500)
    observacoes: str | None = None


class AvariaCheckinInput(BaseModel):
    localizacao: str = Field(min_length=1, max_length=100)
    severidade: AvariaSeveridade
    laudo: str | None = None
    valor_reparo: Decimal | None = Field(default=None, ge=0)
    fotos: list[str] = Field(default_factory=list)
    observacoes: str | None = None


class CheckinConcluirInput(BaseModel):
    """Payload de conclusão do check-in."""

    km_entrada: int = Field(ge=0)
    combustivel_entrada: int = Field(ge=0, le=8)
    checklist_json: dict = Field(default_factory=dict)
    fotos: list[VistoriaFotoInput] = Field(default_factory=list)
    horas_atraso: Decimal = Field(default=Decimal("0"), ge=0)
    km_excedente: int = Field(default=0, ge=0)
    valor_km_excedente: Decimal = Field(default=Decimal("0"), ge=0)
    caucao_devolvida: Decimal = Field(default=Decimal("0"), ge=0)
    caucao_retida: Decimal = Field(default=Decimal("0"), ge=0)
    pendencia_financeira: bool = False
    avarias: list[AvariaCheckinInput] = Field(default_factory=list)
    realizado_em: datetime | None = None
    realizado_por_user_id: uuid.UUID | None = None
    observacoes: str | None = None


class RenovacaoInput(BaseModel):
    nova_devolucao: datetime
    motivo: str | None = Field(default=None, max_length=255)
    aprovado: bool = True


class ReabrirInput(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


class MultaCreate(BaseModel):
    veiculo_id: uuid.UUID
    ocorrido_em: datetime
    orgao: str = Field(min_length=1, max_length=120)
    codigo_infracao: str = Field(min_length=1, max_length=20)
    valor: Decimal = Field(gt=0)
    pontuacao: int = Field(default=0, ge=0)
    ait: str | None = Field(default=None, max_length=40)
    taxa_admin: Decimal = Field(default=Decimal("0"), ge=0)
    observacoes: str | None = None


class MultaUpdate(BaseModel):
    contrato_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    motorista_id: uuid.UUID | None = None
    orgao: str | None = Field(default=None, max_length=120)
    codigo_infracao: str | None = Field(default=None, max_length=20)
    valor: Decimal | None = Field(default=None, gt=0)
    pontuacao: int | None = Field(default=None, ge=0)
    ait: str | None = Field(default=None, max_length=40)
    taxa_admin: Decimal | None = Field(default=None, ge=0)
    observacoes: str | None = None


class AvariaCreate(BaseModel):
    veiculo_id: uuid.UUID
    origem: AvariaOrigem
    localizacao: str = Field(min_length=1, max_length=100)
    severidade: AvariaSeveridade
    contrato_id: uuid.UUID | None = None
    vistoria_id: uuid.UUID | None = None
    laudo: str | None = None
    valor_reparo: Decimal | None = Field(default=None, ge=0)
    fotos: list[str] = Field(default_factory=list)
    observacoes: str | None = None


class AvariaUpdate(BaseModel):
    localizacao: str | None = Field(default=None, max_length=100)
    severidade: AvariaSeveridade | None = None
    laudo: str | None = None
    valor_reparo: Decimal | None = Field(default=None, ge=0)
    observacoes: str | None = None


class AvariaResponsabilidadeInput(BaseModel):
    responsabilidade: AvariaResponsabilidade


class ContratoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    numero: str
    versao: int
    status: ContratoStatus
    reserva_id: uuid.UUID | None
    cliente_id: uuid.UUID
    veiculo_id: uuid.UUID
    valor_total: Decimal
    valor_final: Decimal | None
    pendencia_financeira: bool
    created_at: datetime


class MultaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    veiculo_id: uuid.UUID
    contrato_id: uuid.UUID | None
    ocorrido_em: datetime
    valor: Decimal
    status: MultaStatus


class AvariaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    veiculo_id: uuid.UUID
    contrato_id: uuid.UUID | None
    origem: AvariaOrigem
    severidade: AvariaSeveridade
    status: AvariaStatus
    valor_reparo: Decimal | None
