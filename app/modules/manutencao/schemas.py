"""Schemas Pydantic do módulo Manutenção."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    CadastroStatus,
    CorretivaCausa,
    CorretivaResponsavel,
    EstoqueMovimentoTipo,
    OrdemServicoItemTipo,
    OrdemServicoOrigem,
    OrdemServicoStatus,
    OrdemServicoTipo,
    PneuPosicao,
    PneuStatus,
)


# ------------------------------------------------------------------ Ordem de Serviço
class OrdemServicoCreate(BaseModel):
    veiculo_id: uuid.UUID
    tipo: OrdemServicoTipo
    origem: OrdemServicoOrigem = OrdemServicoOrigem.MANUAL
    fornecedor_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    plano_preventivo_id: uuid.UUID | None = None
    km_entrada: int | None = Field(default=None, ge=0)
    data_previsao: date | None = None
    garantia_dias: int | None = Field(default=None, ge=0)
    garantia_km: int | None = Field(default=None, ge=0)
    causa: CorretivaCausa | None = None
    responsavel_custo: CorretivaResponsavel | None = None
    observacoes: str | None = None
    limite_aprovacao: Decimal | None = Field(default=None, ge=0)


class OrdemServicoUpdate(BaseModel):
    fornecedor_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    km_entrada: int | None = Field(default=None, ge=0)
    km_saida: int | None = Field(default=None, ge=0)
    data_previsao: date | None = None
    garantia_dias: int | None = Field(default=None, ge=0)
    garantia_km: int | None = Field(default=None, ge=0)
    causa: CorretivaCausa | None = None
    responsavel_custo: CorretivaResponsavel | None = None
    observacoes: str | None = None


class OrdemServicoStatusChange(BaseModel):
    status: OrdemServicoStatus
    force: bool = False


class OrdemServicoConcluir(BaseModel):
    km_saida: int | None = Field(default=None, ge=0)
    data_conclusao: date | None = None
    force: bool = False


class OrdemServicoCancelar(BaseModel):
    motivo: str | None = None
    force: bool = False


class OrdemServicoAprovar(BaseModel):
    aprovado_por_user_id: uuid.UUID


class OrdemServicoItemCreate(BaseModel):
    tipo_item: OrdemServicoItemTipo
    descricao: str = Field(min_length=1, max_length=500)
    peca_id: uuid.UUID | None = None
    quantidade: Decimal = Field(default=Decimal("1"), gt=0)
    valor_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    observacoes: str | None = None


class OrdemServicoFotoCreate(BaseModel):
    storage_key: str = Field(min_length=1, max_length=500)
    legenda: str | None = Field(default=None, max_length=255)
    fase: str | None = Field(default=None, max_length=20)
    ordem: int = Field(default=0, ge=0)


class OrdemServicoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    numero: str
    veiculo_id: uuid.UUID
    tipo: OrdemServicoTipo
    origem: OrdemServicoOrigem
    status: OrdemServicoStatus
    fornecedor_id: uuid.UUID | None
    filial_id: uuid.UUID | None
    plano_preventivo_id: uuid.UUID | None
    km_entrada: int | None
    km_saida: int | None
    data_abertura: date
    data_previsao: date | None
    data_conclusao: date | None
    custo_mao_obra: Decimal
    custo_pecas: Decimal
    custo_total: Decimal
    requer_aprovacao: bool
    aprovado_em: datetime | None
    causa: CorretivaCausa | None
    responsavel_custo: CorretivaResponsavel | None
    observacoes: str | None
    created_at: datetime


class OrdemServicoItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    os_id: uuid.UUID
    tipo_item: OrdemServicoItemTipo
    descricao: str
    peca_id: uuid.UUID | None
    quantidade: Decimal
    valor_unitario: Decimal
    valor_total: Decimal
    observacoes: str | None


class OrdemServicoFotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    os_id: uuid.UUID
    storage_key: str
    legenda: str | None
    fase: str | None
    ordem: int


# ---------------------------------------------------------------- Plano Preventivo
class PlanoChecklistItemCreate(BaseModel):
    item_descricao: str = Field(min_length=1, max_length=500)
    ordem: int = Field(default=0, ge=0)


class PlanoPreventivoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    descricao: str | None = None
    categoria_id: uuid.UUID | None = None
    modelo_id: uuid.UUID | None = None
    intervalo_km: int | None = Field(default=None, ge=1)
    intervalo_meses: int | None = Field(default=None, ge=1)
    fornecedor_sugerido_id: uuid.UUID | None = None
    custo_estimado: Decimal = Field(default=Decimal("0"), ge=0)
    automatico: bool = True
    status: CadastroStatus = CadastroStatus.ACTIVE
    checklist: list[PlanoChecklistItemCreate] = Field(default_factory=list)


class PlanoPreventivoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    descricao: str | None = None
    categoria_id: uuid.UUID | None = None
    modelo_id: uuid.UUID | None = None
    intervalo_km: int | None = Field(default=None, ge=1)
    intervalo_meses: int | None = Field(default=None, ge=1)
    fornecedor_sugerido_id: uuid.UUID | None = None
    custo_estimado: Decimal | None = Field(default=None, ge=0)
    automatico: bool | None = None
    status: CadastroStatus | None = None
    checklist: list[PlanoChecklistItemCreate] | None = None


class VeiculoPlanoLink(BaseModel):
    veiculo_id: uuid.UUID
    km_ultima_execucao: int | None = Field(default=None, ge=0)
    data_ultima_execucao: date | None = None


class PreventivaUrgenciaItem(BaseModel):
    veiculo_plano_id: uuid.UUID
    veiculo_id: uuid.UUID
    plano_id: uuid.UUID
    plano_nome: str
    km_atual: int | None
    km_ultima_execucao: int | None
    data_ultima_execucao: date | None
    intervalo_km: int | None
    intervalo_meses: int | None
    km_restante: int | None
    dias_restantes: int | None
    urgencia_pct: float


class PlanoChecklistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plano_id: uuid.UUID
    item_descricao: str
    ordem: int


class PlanoPreventivoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    descricao: str | None
    categoria_id: uuid.UUID | None
    modelo_id: uuid.UUID | None
    intervalo_km: int | None
    intervalo_meses: int | None
    fornecedor_sugerido_id: uuid.UUID | None
    custo_estimado: Decimal
    automatico: bool
    status: CadastroStatus
    created_at: datetime


class VeiculoPlanoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    veiculo_id: uuid.UUID
    plano_id: uuid.UUID
    km_ultima_execucao: int | None
    data_ultima_execucao: date | None


# ------------------------------------------------------------------------- Peça
class PecaCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=60)
    nome: str = Field(min_length=2, max_length=200)
    categoria_codigo: str | None = Field(default=None, max_length=60)
    unidade: str = Field(default="UN", max_length=10)
    custo_medio: Decimal = Field(default=Decimal("0"), ge=0)
    status: CadastroStatus = CadastroStatus.ACTIVE


class PecaUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=60)
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    categoria_codigo: str | None = None
    unidade: str | None = Field(default=None, max_length=10)
    custo_medio: Decimal | None = Field(default=None, ge=0)
    status: CadastroStatus | None = None


class PecaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nome: str
    categoria_codigo: str | None
    unidade: str
    custo_medio: Decimal
    status: CadastroStatus
    created_at: datetime


# ---------------------------------------------------------------------- Estoque
class EstoqueEnsure(BaseModel):
    filial_id: uuid.UUID
    quantidade_minima: Decimal = Field(default=Decimal("0"), ge=0)
    quantidade_maxima: Decimal | None = Field(default=None, ge=0)
    localizacao: str | None = Field(default=None, max_length=100)


class EstoqueMovimentoBase(BaseModel):
    filial_id: uuid.UUID
    quantidade: Decimal = Field(gt=0)
    custo_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    observacoes: str | None = None


class EstoqueEntrada(EstoqueMovimentoBase):
    pass


class EstoqueSaida(EstoqueMovimentoBase):
    os_id: uuid.UUID | None = None


class EstoqueAjuste(BaseModel):
    filial_id: uuid.UUID
    quantidade: Decimal
    custo_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    observacoes: str | None = None


class EstoqueTransferencia(BaseModel):
    filial_origem_id: uuid.UUID
    filial_destino_id: uuid.UUID
    quantidade: Decimal = Field(gt=0)
    observacoes: str | None = None


class EstoqueAlertaItem(BaseModel):
    estoque_id: uuid.UUID
    peca_id: uuid.UUID
    peca_codigo: str
    peca_nome: str
    filial_id: uuid.UUID
    quantidade_atual: Decimal
    quantidade_minima: Decimal


class EstoquePecaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    peca_id: uuid.UUID
    filial_id: uuid.UUID
    quantidade_atual: Decimal
    quantidade_minima: Decimal
    quantidade_maxima: Decimal | None
    localizacao: str | None


class EstoqueMovimentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    peca_id: uuid.UUID
    filial_id: uuid.UUID
    filial_destino_id: uuid.UUID | None
    tipo: EstoqueMovimentoTipo
    quantidade: Decimal
    custo_unitario: Decimal
    os_id: uuid.UUID | None
    observacoes: str | None
    ocorrido_em: datetime


class EstoqueEntradaRequest(EstoqueEntrada):
    peca_id: uuid.UUID


class EstoqueSaidaRequest(EstoqueSaida):
    peca_id: uuid.UUID


class EstoqueAjusteRequest(EstoqueAjuste):
    peca_id: uuid.UUID


class EstoqueTransferenciaRequest(EstoqueTransferencia):
    peca_id: uuid.UUID


# ------------------------------------------------------------------------- Pneu
class PneuCreate(BaseModel):
    numero_fogo: str = Field(min_length=1, max_length=50)
    marca: str = Field(min_length=1, max_length=100)
    modelo: str | None = Field(default=None, max_length=100)
    medida: str = Field(min_length=1, max_length=30)
    vida_util_km: int | None = Field(default=None, ge=1)
    observacoes: str | None = None


class PneuUpdate(BaseModel):
    marca: str | None = Field(default=None, min_length=1, max_length=100)
    modelo: str | None = None
    medida: str | None = Field(default=None, min_length=1, max_length=30)
    vida_util_km: int | None = Field(default=None, ge=1)
    observacoes: str | None = None


class PneuInstalar(BaseModel):
    veiculo_id: uuid.UUID
    posicao: PneuPosicao
    km: int = Field(ge=0)


class PneuRodizio(BaseModel):
    posicao_destino: PneuPosicao
    km: int | None = Field(default=None, ge=0)
    observacoes: str | None = None


class PneuInspecionar(BaseModel):
    sulco_mm: Decimal = Field(ge=0)
    km: int | None = Field(default=None, ge=0)
    observacoes: str | None = None


class PneuDescartar(BaseModel):
    motivo: str | None = None
    km: int | None = Field(default=None, ge=0)


class PneuAlertaItem(BaseModel):
    pneu_id: uuid.UUID
    numero_fogo: str
    veiculo_id: uuid.UUID | None
    km_percorrido: int
    vida_util_km: int
    uso_pct: float


class PneuRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    numero_fogo: str
    marca: str
    modelo: str | None
    medida: str
    veiculo_id: uuid.UUID | None
    posicao: PneuPosicao | None
    km_instalacao: int | None
    km_atual: int | None
    vida_util_km: int | None
    sulco_mm: Decimal | None
    status: PneuStatus
    observacoes: str | None
    created_at: datetime


class PneuHistoricoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pneu_id: uuid.UUID
    veiculo_id: uuid.UUID | None
    posicao: PneuPosicao | None
    km_evento: int | None
    tipo_evento: str
    observacoes: str | None
    ocorrido_em: datetime
