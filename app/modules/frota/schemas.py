"""Schemas Pydantic do módulo Frota."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.enums import (
    AcessorioTipo,
    CadastroStatus,
    CombustivelUnidade,
    DocumentoVeiculoStatus,
    DocumentoVeiculoTipo,
    TelemetriaConnStatus,
    TelemetriaEventoTipo,
    VeiculoPropriedade,
    VeiculoStatus,
)
from app.shared.value_objects import only_digits

_PLACA_CLEAN = re.compile(r"[\s\-]+")
_PLACA_VALID = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$|^[A-Z]{3}[0-9]{4}$")


def _normalize_placa(value: str) -> str:
    cleaned = _PLACA_CLEAN.sub("", value.strip().upper())
    return cleaned[:8]


def _validate_placa_format(cleaned: str) -> None:
    core = cleaned[:7]
    if len(core) < 7 or not _PLACA_VALID.match(core):
        raise ValueError("Placa inválida. Use Mercosul (ABC1D23) ou antigo (ABC1234).")


# ------------------------------------------------------------------ Categoria
class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    descricao: str | None = None
    capacidade_passageiros: int = Field(default=5, ge=1, le=60)
    capacidade_porta_malas: str | None = None
    transmissao_tipica: str | None = None
    imagem_url: str | None = None
    ordem: int = Field(default=0, ge=0)
    grupo_tarifario: str | None = None
    status: CadastroStatus = CadastroStatus.ACTIVE


class CategoriaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    descricao: str | None = None
    capacidade_passageiros: int | None = Field(default=None, ge=1, le=60)
    capacidade_porta_malas: str | None = None
    transmissao_tipica: str | None = None
    imagem_url: str | None = None
    ordem: int | None = Field(default=None, ge=0)
    grupo_tarifario: str | None = None
    status: CadastroStatus | None = None


class CategoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    descricao: str | None
    capacidade_passageiros: int
    ordem: int
    grupo_tarifario: str | None
    status: CadastroStatus
    created_at: datetime


# ---------------------------------------------------------------------- Marca
class MarcaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    logo_url: str | None = None
    pais_origem: str | None = None
    status: CadastroStatus = CadastroStatus.ACTIVE


class MarcaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    logo_url: str | None = None
    pais_origem: str | None = None
    status: CadastroStatus | None = None


class MarcaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    logo_url: str | None
    pais_origem: str | None
    status: CadastroStatus
    created_at: datetime


# ---------------------------------------------------------------- Combustível
class CombustivelCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    unidade: CombustivelUnidade = CombustivelUnidade.LITRO
    preco_referencia: Decimal = Field(default=Decimal("0"), ge=0)
    status: CadastroStatus = CadastroStatus.ACTIVE


class CombustivelUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    unidade: CombustivelUnidade | None = None
    preco_referencia: Decimal | None = Field(default=None, ge=0)
    status: CadastroStatus | None = None


class CombustivelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    unidade: CombustivelUnidade
    preco_referencia: Decimal
    status: CadastroStatus
    created_at: datetime


# --------------------------------------------------------------------- Modelo
class ModeloCreate(BaseModel):
    marca_id: uuid.UUID
    categoria_padrao_id: uuid.UUID | None = None
    nome: str = Field(min_length=2, max_length=200)
    versao: str | None = None
    motorizacao: str | None = None
    cambio: str | None = None
    portas: int | None = Field(default=None, ge=2, le=6)
    capacidade_tanque: Decimal | None = Field(default=None, ge=0)
    consumo_medio_km_l: Decimal | None = Field(default=None, ge=0)
    codigo_fipe: str | None = None
    status: CadastroStatus = CadastroStatus.ACTIVE


class ModeloUpdate(BaseModel):
    marca_id: uuid.UUID | None = None
    categoria_padrao_id: uuid.UUID | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    versao: str | None = None
    motorizacao: str | None = None
    cambio: str | None = None
    portas: int | None = Field(default=None, ge=2, le=6)
    capacidade_tanque: Decimal | None = Field(default=None, ge=0)
    consumo_medio_km_l: Decimal | None = Field(default=None, ge=0)
    codigo_fipe: str | None = None
    status: CadastroStatus | None = None


class ModeloRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    marca_id: uuid.UUID
    categoria_padrao_id: uuid.UUID | None
    nome: str
    versao: str | None
    motorizacao: str | None
    status: CadastroStatus
    created_at: datetime


# ------------------------------------------------------------------- Acessório
class AcessorioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    descricao: str | None = None
    tipo: AcessorioTipo = AcessorioTipo.FIXO
    valor_diaria: Decimal = Field(default=Decimal("0"), ge=0)
    estoque_disponivel: int = Field(default=0, ge=0)
    foto_url: str | None = None
    status: CadastroStatus = CadastroStatus.ACTIVE


class AcessorioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    descricao: str | None = None
    tipo: AcessorioTipo | None = None
    valor_diaria: Decimal | None = Field(default=None, ge=0)
    estoque_disponivel: int | None = Field(default=None, ge=0)
    foto_url: str | None = None
    status: CadastroStatus | None = None


class AcessorioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    tipo: AcessorioTipo
    valor_diaria: Decimal
    estoque_disponivel: int
    status: CadastroStatus
    created_at: datetime


# --------------------------------------------------------------------- Veículo
class VeiculoCreate(BaseModel):
    placa: str = Field(min_length=7, max_length=10)
    renavam: str | None = None
    chassi: str | None = None
    ano_fabricacao: int = Field(ge=1980, le=2100)
    ano_modelo: int = Field(ge=1980, le=2100)
    cor: str | None = None
    categoria_id: uuid.UUID | None = None
    marca_id: uuid.UUID
    modelo_id: uuid.UUID
    combustivel_id: uuid.UUID
    filial_id: uuid.UUID | None = None
    fornecedor_id: uuid.UUID | None = None
    propriedade: VeiculoPropriedade = VeiculoPropriedade.PROPRIA
    data_compra: date | None = None
    valor_aquisicao: Decimal | None = Field(default=None, ge=0)
    km_inicial: int | None = Field(default=None, ge=0)
    km_atual: int | None = Field(default=None, ge=0)
    valor_fipe: Decimal | None = Field(default=None, ge=0)
    valor_mercado: Decimal | None = Field(default=None, ge=0)
    proprietario_nome: str | None = None
    observacoes: str | None = None
    nivel_combustivel_atual: int = Field(default=8, ge=0, le=8)
    contrato_fornecedor_id: uuid.UUID | None = None
    publicar_site: bool = True
    exige_aprovacao_fornecedor: bool = True

    @field_validator("placa")
    @classmethod
    def _placa(cls, value: str) -> str:
        normalized = _normalize_placa(value)
        _validate_placa_format(normalized)
        return normalized[:7]

    @field_validator("renavam")
    @classmethod
    def _renavam(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)[:11]
        if not digits:
            raise ValueError("RENAVAM inválido.")
        return digits

    @field_validator("chassi")
    @classmethod
    def _chassi(cls, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = value.strip().upper()[:17]
        if len(cleaned) < 11:
            raise ValueError("Chassi inválido.")
        return cleaned


class VeiculoUpdate(BaseModel):
    placa: str | None = Field(default=None, min_length=7, max_length=10)
    renavam: str | None = None
    chassi: str | None = None
    ano_fabricacao: int | None = Field(default=None, ge=1980, le=2100)
    ano_modelo: int | None = Field(default=None, ge=1980, le=2100)
    cor: str | None = None
    categoria_id: uuid.UUID | None = None
    marca_id: uuid.UUID | None = None
    modelo_id: uuid.UUID | None = None
    combustivel_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    fornecedor_id: uuid.UUID | None = None
    propriedade: VeiculoPropriedade | None = None
    data_compra: date | None = None
    valor_aquisicao: Decimal | None = Field(default=None, ge=0)
    km_inicial: int | None = Field(default=None, ge=0)
    km_atual: int | None = Field(default=None, ge=0)
    valor_fipe: Decimal | None = Field(default=None, ge=0)
    valor_mercado: Decimal | None = Field(default=None, ge=0)
    proprietario_nome: str | None = None
    observacoes: str | None = None
    nivel_combustivel_atual: int | None = Field(default=None, ge=0, le=8)
    contrato_fornecedor_id: uuid.UUID | None = None
    publicar_site: bool | None = None
    exige_aprovacao_fornecedor: bool | None = None

    @field_validator("placa")
    @classmethod
    def _placa(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = _normalize_placa(value)
        _validate_placa_format(normalized)
        return normalized[:7]

    @field_validator("renavam")
    @classmethod
    def _renavam(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)[:11]
        if not digits:
            raise ValueError("RENAVAM inválido.")
        return digits

    @field_validator("chassi")
    @classmethod
    def _chassi(cls, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = value.strip().upper()[:17]
        if len(cleaned) < 11:
            raise ValueError("Chassi inválido.")
        return cleaned


class VeiculoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    placa: str
    renavam: str | None
    chassi: str | None
    ano_fabricacao: int
    ano_modelo: int
    categoria_id: uuid.UUID
    marca_id: uuid.UUID
    modelo_id: uuid.UUID
    combustivel_id: uuid.UUID
    filial_id: uuid.UUID | None
    status: VeiculoStatus
    propriedade: VeiculoPropriedade
    km_atual: int | None
    motivo_bloqueio: str | None
    data_baixa: date | None
    created_at: datetime


# ---------------------------------------------------------- Veículo × Acessório
class VeiculoAcessorioLink(BaseModel):
    acessorio_id: uuid.UUID
    data_instalacao: date | None = None
    observacoes: str | None = None


class VeiculoAcessorioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    veiculo_id: uuid.UUID
    acessorio_id: uuid.UUID
    data_instalacao: date | None
    observacoes: str | None
    created_at: datetime


# ------------------------------------------------------------------------ Foto
class VeiculoFotoCreate(BaseModel):
    storage_key: str = Field(min_length=1, max_length=500)
    legenda: str | None = None
    tirada_em: date | None = None
    ordem: int = Field(default=0, ge=0)


class VeiculoFotoUpdate(BaseModel):
    legenda: str | None = None
    tirada_em: date | None = None
    ordem: int | None = Field(default=None, ge=0)


class VeiculoFotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    veiculo_id: uuid.UUID
    storage_key: str
    legenda: str | None
    tirada_em: date | None
    ordem: int
    created_at: datetime


# ------------------------------------------------------------------ Documento
class DocumentoCreate(BaseModel):
    veiculo_id: uuid.UUID
    tipo: DocumentoVeiculoTipo
    numero: str | None = None
    orgao_emissor: str | None = None
    data_emissao: date | None = None
    data_validade: date
    arquivo_key: str | None = None
    observacoes: str | None = None


class DocumentoUpdate(BaseModel):
    tipo: DocumentoVeiculoTipo | None = None
    numero: str | None = None
    orgao_emissor: str | None = None
    data_emissao: date | None = None
    data_validade: date | None = None
    arquivo_key: str | None = None
    observacoes: str | None = None


class DocumentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    veiculo_id: uuid.UUID
    tipo: DocumentoVeiculoTipo
    numero: str | None
    data_validade: date | None
    status: DocumentoVeiculoStatus
    versao: int
    created_at: datetime


# -------------------------------------------------------------- Telemetria
class TelemetriaDispositivoUpsert(BaseModel):
    veiculo_id: uuid.UUID
    provedor: str = Field(min_length=2, max_length=100)
    equipamento_id: str = Field(min_length=1, max_length=100)
    conn_status: TelemetriaConnStatus = TelemetriaConnStatus.OFFLINE
    lat: Decimal | None = None
    lng: Decimal | None = None
    ultima_posicao_em: datetime | None = None
    km_telemetria: int | None = Field(default=None, ge=0)
    bloqueio_remoto: bool = False
    observacoes: str | None = None


class TelemetriaDispositivoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    veiculo_id: uuid.UUID
    provedor: str
    equipamento_id: str
    conn_status: TelemetriaConnStatus
    lat: Decimal | None
    lng: Decimal | None
    ultima_posicao_em: datetime | None
    km_telemetria: int | None
    bloqueio_remoto: bool
    created_at: datetime


class TelemetriaEventoCreate(BaseModel):
    dispositivo_id: uuid.UUID
    veiculo_id: uuid.UUID
    tipo: TelemetriaEventoTipo
    descricao: str | None = None
    lat: Decimal | None = None
    lng: Decimal | None = None
    velocidade: Decimal | None = Field(default=None, ge=0)
    ocorrido_em: datetime
    payload_json: str | None = None


class TelemetriaEventoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    dispositivo_id: uuid.UUID
    veiculo_id: uuid.UUID
    tipo: TelemetriaEventoTipo
    descricao: str | None
    ocorrido_em: datetime
    created_at: datetime
