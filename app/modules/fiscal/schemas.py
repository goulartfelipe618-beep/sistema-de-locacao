"""Schemas Pydantic do módulo Fiscal (§10)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    CancelamentoEventoTipo,
    CancelamentoStatus,
    FiscalDocumentoTipo,
    FiscalXmlDirecao,
    FiscalXmlTipo,
    ImpostoTipo,
    NfeOperacao,
    NfeStatus,
    NfseStatus,
    RegimeTributario,
)


# ============================================================ 10.5 Impostos
class ImpostoConfigCreate(BaseModel):
    filial_id: uuid.UUID | None = None
    regime: RegimeTributario = RegimeTributario.SIMPLES_NACIONAL
    vigencia_inicio: date
    vigencia_fim: date | None = None
    nfse_automatica: bool = False
    ativo: bool = True
    observacoes: str | None = None


class ImpostoConfigUpdate(BaseModel):
    regime: RegimeTributario | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    nfse_automatica: bool | None = None
    ativo: bool | None = None
    observacoes: str | None = None


class ImpostoConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filial_id: uuid.UUID | None
    regime: RegimeTributario
    vigencia_inicio: date
    vigencia_fim: date | None
    nfse_automatica: bool
    ativo: bool


class AliquotaCreate(BaseModel):
    config_id: uuid.UUID
    tipo: ImpostoTipo
    aliquota_percentual: Decimal = Field(ge=0)
    servico_produto_codigo: str | None = Field(default=None, max_length=40)
    descricao: str | None = Field(default=None, max_length=200)
    retencao: bool = False
    vigencia_inicio: date
    vigencia_fim: date | None = None


class AliquotaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    config_id: uuid.UUID
    tipo: ImpostoTipo
    servico_produto_codigo: str | None
    descricao: str | None
    aliquota_percentual: Decimal
    retencao: bool
    vigencia_inicio: date
    vigencia_fim: date | None


class ApuracaoImpostoLinha(BaseModel):
    tipo: str
    documentos: int
    base_calculo: Decimal
    valor_imposto: Decimal


# ============================================================ 10.1 NFS-e
class NfseCreate(BaseModel):
    filial_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    contrato_id: uuid.UUID | None = None
    fatura_id: uuid.UUID | None = None
    valor_servico: Decimal = Field(gt=0)
    municipio_ibge: str | None = Field(default=None, max_length=10)
    municipio_nome: str | None = Field(default=None, max_length=120)
    aliquota_iss: Decimal | None = Field(default=None, ge=0)
    retencao_iss: bool = False
    discriminacao: str | None = None


class NfseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    serie: str
    status: NfseStatus
    contrato_id: uuid.UUID | None
    fatura_id: uuid.UUID | None
    cliente_id: uuid.UUID | None
    filial_id: uuid.UUID
    municipio_nome: str | None
    valor_servico: Decimal
    aliquota_iss: Decimal
    valor_iss: Decimal
    valor_iss_retido: Decimal
    retencao_iss: bool
    chave_acesso: str | None
    protocolo: str | None
    emitida_em: datetime | None
    autorizada_em: datetime | None
    provedor: str
    automatica: bool


class CancelarInput(BaseModel):
    motivo: str = Field(min_length=1, max_length=255)
    justificativa_completa: str | None = None


# ============================================================ 10.2 NF-e
class NfeItemInput(BaseModel):
    descricao: str = Field(min_length=1, max_length=255)
    quantidade: Decimal = Field(default=Decimal("1"), gt=0)
    valor_unitario: Decimal = Field(ge=0)
    codigo: str | None = Field(default=None, max_length=40)
    ncm: str | None = Field(default=None, max_length=10)
    cfop: str | None = Field(default=None, max_length=10)
    icms_aliquota: Decimal = Field(default=Decimal("0"), ge=0)
    ipi_aliquota: Decimal = Field(default=Decimal("0"), ge=0)
    produto_ref_tipo: str | None = Field(default=None, max_length=20)
    produto_ref_id: uuid.UUID | None = None


class NfeCreate(BaseModel):
    filial_id: uuid.UUID
    destinatario_nome: str = Field(min_length=1, max_length=160)
    destinatario_doc: str | None = Field(default=None, max_length=20)
    destinatario_id: uuid.UUID | None = None
    operacao: NfeOperacao = NfeOperacao.VENDA
    veiculo_id: uuid.UUID | None = None
    natureza_operacao: str | None = Field(default=None, max_length=120)
    cfop_padrao: str | None = Field(default=None, max_length=10)
    itens: list[NfeItemInput] = Field(default_factory=list)


class NfeItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    descricao: str
    codigo: str | None
    ncm: str | None
    cfop: str | None
    quantidade: Decimal
    valor_unitario: Decimal
    valor_total: Decimal
    icms_aliquota: Decimal
    icms_valor: Decimal
    ipi_aliquota: Decimal
    ipi_valor: Decimal


class NfeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    serie: str
    status: NfeStatus
    operacao: NfeOperacao
    destinatario_nome: str
    destinatario_doc: str | None
    filial_id: uuid.UUID
    veiculo_id: uuid.UUID | None
    valor_total: Decimal
    natureza_operacao: str | None
    cfop_padrao: str | None
    chave_acesso: str | None
    protocolo: str | None
    emitida_em: datetime | None
    autorizada_em: datetime | None
    provedor: str


# ============================================================ 10.3 XML
class XmlImportInput(BaseModel):
    conteudo_xml: str = Field(min_length=1)
    filial_id: uuid.UUID | None = None
    filename: str | None = Field(default=None, max_length=200)


class XmlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: FiscalXmlTipo
    direcao: FiscalXmlDirecao
    chave_acesso: str | None
    hash_sha256: str
    documento_tipo: str | None
    documento_id: uuid.UUID | None
    filial_id: uuid.UUID | None
    periodo_ref: date | None
    filename: str
    tamanho_bytes: int
    fornecedor_cnpj: str | None
    titulo_pagar_id: uuid.UUID | None
    created_at: datetime


# ============================================================ 10.4 Cancelamentos
class CancelamentoCreate(BaseModel):
    documento_tipo: FiscalDocumentoTipo
    documento_id: uuid.UUID
    tipo_evento: CancelamentoEventoTipo = CancelamentoEventoTipo.CANCELAMENTO
    motivo: str = Field(min_length=1, max_length=255)
    justificativa_completa: str | None = None


class CancelamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: str
    documento_tipo: FiscalDocumentoTipo
    documento_id: uuid.UUID
    tipo_evento: CancelamentoEventoTipo
    motivo: str
    solicitado_em: datetime
    processado_em: datetime | None
    protocolo_retorno: str | None
    status: CancelamentoStatus
    fora_do_prazo: bool


class PrazoCancelamentoCreate(BaseModel):
    tipo_documento: FiscalDocumentoTipo
    horas_limite: int = Field(default=24, ge=1)
    uf: str | None = Field(default=None, max_length=2)
    municipio_ibge: str | None = Field(default=None, max_length=10)
    ativo: bool = True
    descricao: str | None = Field(default=None, max_length=200)


class PrazoCancelamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_documento: FiscalDocumentoTipo
    uf: str | None
    municipio_ibge: str | None
    horas_limite: int
    ativo: bool
    descricao: str | None
