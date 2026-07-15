"""Schemas Pydantic do módulo Comercial / CRM (§7)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    CrmCampanhaCanal,
    CrmCampanhaPublico,
    CrmCampanhaStatus,
    CrmCupomStatus,
    CrmCupomTipo,
    CrmEstagio,
    CrmInteracaoTipo,
    CrmOrigemLead,
    CrmPropostaStatus,
)


# ============================================================ 7.1 Funil
class OportunidadeCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    estagio: CrmEstagio = CrmEstagio.LEAD
    origem_lead: CrmOrigemLead = CrmOrigemLead.OUTRO
    vendedor_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    cotacao_id: uuid.UUID | None = None
    reserva_id: uuid.UUID | None = None
    valor_estimado: Decimal = Field(default=Decimal("0"), ge=0)
    data_prevista_fechamento: date | None = None
    observacoes: str | None = None


class OportunidadeUpdate(BaseModel):
    titulo: str | None = Field(default=None, max_length=200)
    origem_lead: CrmOrigemLead | None = None
    vendedor_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    valor_estimado: Decimal | None = Field(default=None, ge=0)
    data_prevista_fechamento: date | None = None
    observacoes: str | None = None


class MoverEstagioInput(BaseModel):
    estagio: CrmEstagio


class MarcarPerdidoInput(BaseModel):
    motivo_perda: str = Field(min_length=1, max_length=255)


class MarcarGanhoInput(BaseModel):
    reserva_id: uuid.UUID | None = None


class InteracaoCreate(BaseModel):
    tipo: CrmInteracaoTipo = CrmInteracaoTipo.NOTA
    descricao: str = Field(min_length=1)
    ocorrido_em: datetime | None = None


class OportunidadeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    titulo: str
    estagio: CrmEstagio
    origem_lead: CrmOrigemLead
    vendedor_id: uuid.UUID | None
    cliente_id: uuid.UUID | None
    cotacao_id: uuid.UUID | None
    reserva_id: uuid.UUID | None
    valor_estimado: Decimal
    data_prevista_fechamento: date | None
    motivo_perda: str | None
    ultima_interacao_em: datetime | None
    created_at: datetime


class InteracaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    oportunidade_id: uuid.UUID
    tipo: CrmInteracaoTipo
    descricao: str
    ocorrido_em: datetime


# ============================================================ 7.2 Propostas
class PropostaItemInput(BaseModel):
    descricao: str = Field(min_length=1, max_length=255)
    categoria_id: uuid.UUID | None = None
    veiculo_id: uuid.UUID | None = None
    quantidade: Decimal = Field(default=Decimal("1"), gt=0)
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    dias: int = Field(default=1, ge=1)
    valor_unitario: Decimal = Field(default=Decimal("0"), ge=0)


class PropostaCreate(BaseModel):
    cliente_id: uuid.UUID | None = None
    oportunidade_id: uuid.UUID | None = None
    vendedor_id: uuid.UUID | None = None
    campanha_id: uuid.UUID | None = None
    cupom_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    validade_em: date | None = None
    condicoes_comerciais: str | None = None
    observacoes: str | None = None
    itens: list[PropostaItemInput] = Field(default_factory=list)


class PropostaUpdate(BaseModel):
    cliente_id: uuid.UUID | None = None
    vendedor_id: uuid.UUID | None = None
    campanha_id: uuid.UUID | None = None
    cupom_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    validade_em: date | None = None
    condicoes_comerciais: str | None = None
    observacoes: str | None = None
    itens: list[PropostaItemInput] | None = None


class PropostaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    versao: int
    cliente_id: uuid.UUID | None
    status: CrmPropostaStatus
    validade_em: date | None
    valor_total: Decimal
    enviada_em: datetime | None
    aceita_em: datetime | None
    created_at: datetime


# ============================================================ 7.3 Campanhas
class CampanhaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=160)
    inicio_em: date | None = None
    fim_em: date | None = None
    canal: CrmCampanhaCanal = CrmCampanhaCanal.EMAIL
    publico_alvo: CrmCampanhaPublico = CrmCampanhaPublico.TODOS
    categoria_cliente: str | None = Field(default=None, max_length=60)
    dias_inativo: int = Field(default=90, ge=1)
    desconto_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    desconto_valor: Decimal | None = Field(default=None, ge=0)
    cupom_id: uuid.UUID | None = None
    mensagem_assunto: str | None = Field(default=None, max_length=200)
    mensagem_corpo: str | None = None


class CampanhaUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=160)
    inicio_em: date | None = None
    fim_em: date | None = None
    canal: CrmCampanhaCanal | None = None
    publico_alvo: CrmCampanhaPublico | None = None
    categoria_cliente: str | None = Field(default=None, max_length=60)
    dias_inativo: int | None = Field(default=None, ge=1)
    desconto_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    desconto_valor: Decimal | None = Field(default=None, ge=0)
    cupom_id: uuid.UUID | None = None
    mensagem_assunto: str | None = Field(default=None, max_length=200)
    mensagem_corpo: str | None = None


class CampanhaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nome: str
    status: CrmCampanhaStatus
    canal: CrmCampanhaCanal
    publico_alvo: CrmCampanhaPublico
    inicio_em: date | None
    fim_em: date | None
    enviados: int
    abertos: int
    convertidos: int
    created_at: datetime


# ============================================================ 7.4 Cupons
class CupomCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    tipo: CrmCupomTipo = CrmCupomTipo.PERCENTUAL
    valor: Decimal = Field(gt=0)
    categoria_id: uuid.UUID | None = None
    valor_minimo: Decimal = Field(default=Decimal("0"), ge=0)
    primeira_locacao_apenas: bool = False
    inicio_em: date | None = None
    fim_em: date | None = None
    limite_uso_total: int | None = Field(default=None, ge=1)
    limite_uso_cliente: int | None = Field(default=None, ge=1)
    campanha_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    descricao: str | None = Field(default=None, max_length=255)


class CupomUpdate(BaseModel):
    tipo: CrmCupomTipo | None = None
    valor: Decimal | None = Field(default=None, gt=0)
    categoria_id: uuid.UUID | None = None
    valor_minimo: Decimal | None = Field(default=None, ge=0)
    primeira_locacao_apenas: bool | None = None
    inicio_em: date | None = None
    fim_em: date | None = None
    limite_uso_total: int | None = Field(default=None, ge=1)
    limite_uso_cliente: int | None = Field(default=None, ge=1)
    status: CrmCupomStatus | None = None
    descricao: str | None = Field(default=None, max_length=255)


class CupomValidarInput(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    cliente_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    valor_base: Decimal = Field(default=Decimal("0"), ge=0)


class CupomValidacaoResult(BaseModel):
    ok: bool
    desconto: Decimal = Decimal("0")
    motivo: str | None = None
    cupom_id: uuid.UUID | None = None
    codigo: str | None = None


class CupomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    tipo: CrmCupomTipo
    valor: Decimal
    valor_minimo: Decimal
    primeira_locacao_apenas: bool
    inicio_em: date | None
    fim_em: date | None
    limite_uso_total: int | None
    limite_uso_cliente: int | None
    usos_totais: int
    status: CrmCupomStatus
    created_at: datetime


# ============================================================ 7.5 Fidelidade
class FidelidadeRegraInput(BaseModel):
    nome: str = Field(default="Programa de Fidelidade", max_length=120)
    pontos_por_real: Decimal = Field(default=Decimal("1"), ge=0)
    pontos_por_diaria: Decimal = Field(default=Decimal("0"), ge=0)
    valor_por_ponto: Decimal = Field(default=Decimal("0.10"), ge=0)
    validade_meses: int = Field(default=12, ge=1)
    ativo: bool = True


class FidelidadeTierInput(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    pontos_minimos: int = Field(default=0, ge=0)
    beneficio_descricao: str | None = Field(default=None, max_length=255)
    ordem: int = Field(default=0, ge=0)


class FidelidadeResgatarInput(BaseModel):
    cliente_id: uuid.UUID
    pontos: int = Field(gt=0)
    reserva_id: uuid.UUID | None = None


class FidelidadeContaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_id: uuid.UUID
    pontos_saldo: int
    pontos_historico_total: int
    tier_id: uuid.UUID | None


class FidelidadeMovimentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conta_id: uuid.UUID
    tipo: str
    pontos: int
    origem: str
    descricao: str | None
    created_at: datetime
    expira_em: datetime | None
