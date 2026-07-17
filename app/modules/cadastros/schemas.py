"""Schemas Pydantic do módulo de Cadastros."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.enums import ClienteStatus, PersonType
from app.shared.value_objects import is_valid_cnpj, is_valid_cpf, only_digits


class TabelaAuxiliarBase(BaseModel):
    """Campos comuns de tabela auxiliar."""

    grupo: str = Field(min_length=2, max_length=60)
    codigo: str = Field(min_length=1, max_length=60)
    descricao: str = Field(min_length=1, max_length=200)
    ativo: bool = True
    ordem: int = 0


class TabelaAuxiliarCreate(TabelaAuxiliarBase):
    """Criação de item auxiliar."""


class TabelaAuxiliarUpdate(BaseModel):
    """Atualização parcial de item auxiliar."""

    descricao: str | None = Field(default=None, min_length=1, max_length=200)
    ativo: bool | None = None
    ordem: int | None = None


class TabelaAuxiliarRead(BaseModel):
    """Saída de item auxiliar."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    grupo: str
    codigo: str
    descricao: str
    ativo: bool
    ordem: int
    sistema: bool
    created_at: datetime


class ClienteBase(BaseModel):
    """Campos de cliente compartilhados."""

    person_type: PersonType
    status: ClienteStatus = ClienteStatus.ACTIVE
    nome: str = Field(min_length=2, max_length=200)
    nome_fantasia: str | None = Field(default=None, max_length=200)
    cpf: str | None = Field(default=None, max_length=14)
    cnpj: str | None = Field(default=None, max_length=18)
    rg: str | None = Field(default=None, max_length=20)
    ie: str | None = Field(default=None, max_length=30)
    data_nascimento: date | None = None
    estado_civil: str | None = Field(default=None, max_length=40)
    profissao: str | None = Field(default=None, max_length=100)
    representante_legal: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    telefone: str | None = Field(default=None, max_length=20)
    celular: str | None = Field(default=None, max_length=20)
    cep: str | None = Field(default=None, max_length=9)
    endereco: str | None = Field(default=None, max_length=255)
    numero: str | None = Field(default=None, max_length=20)
    complemento: str | None = Field(default=None, max_length=100)
    bairro: str | None = Field(default=None, max_length=100)
    cidade: str | None = Field(default=None, max_length=100)
    uf: str | None = Field(default=None, max_length=2)
    categoria_codigo: str | None = Field(default=None, max_length=60)
    limite_credito: Decimal = Field(default=Decimal("0.00"), ge=0)
    observacoes: str | None = None
    filial_id: uuid.UUID | None = None

    @field_validator("cpf")
    @classmethod
    def _validate_cpf(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        if not is_valid_cpf(digits):
            raise ValueError("CPF inválido.")
        return digits

    @field_validator("cnpj")
    @classmethod
    def _validate_cnpj(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        if not is_valid_cnpj(digits):
            raise ValueError("CNPJ inválido.")
        return digits

    @field_validator("cep")
    @classmethod
    def _normalize_cep(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        return digits[:8] if digits else None

    @field_validator("uf")
    @classmethod
    def _normalize_uf(cls, value: str | None) -> str | None:
        if not value:
            return None
        return value.strip().upper()[:2]

    @model_validator(mode="after")
    def _require_document_by_type(self) -> ClienteBase:
        if self.person_type == PersonType.NATURAL and not self.cpf:
            raise ValueError("CPF é obrigatório para pessoa física.")
        if self.person_type == PersonType.LEGAL and not self.cnpj:
            raise ValueError("CNPJ é obrigatório para pessoa jurídica.")
        if self.person_type == PersonType.NATURAL:
            self.cnpj = None
        if self.person_type == PersonType.LEGAL:
            self.cpf = None
        return self


class ClienteCreate(ClienteBase):
    """Criação de cliente."""


class ClienteUpdate(BaseModel):
    """Atualização parcial de cliente."""

    status: ClienteStatus | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    nome_fantasia: str | None = Field(default=None, max_length=200)
    rg: str | None = Field(default=None, max_length=20)
    ie: str | None = Field(default=None, max_length=30)
    data_nascimento: date | None = None
    estado_civil: str | None = Field(default=None, max_length=40)
    profissao: str | None = Field(default=None, max_length=100)
    representante_legal: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    telefone: str | None = Field(default=None, max_length=20)
    celular: str | None = Field(default=None, max_length=20)
    cep: str | None = Field(default=None, max_length=9)
    endereco: str | None = Field(default=None, max_length=255)
    numero: str | None = Field(default=None, max_length=20)
    complemento: str | None = Field(default=None, max_length=100)
    bairro: str | None = Field(default=None, max_length=100)
    cidade: str | None = Field(default=None, max_length=100)
    uf: str | None = Field(default=None, max_length=2)
    categoria_codigo: str | None = Field(default=None, max_length=60)
    limite_credito: Decimal | None = Field(default=None, ge=0)
    observacoes: str | None = None
    filial_id: uuid.UUID | None = None
    blacklist: bool | None = None
    motivo_bloqueio: str | None = Field(default=None, max_length=255)

    @field_validator("cep")
    @classmethod
    def _normalize_cep(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value == "":
            return None
        return only_digits(value)[:8]

    @field_validator("uf")
    @classmethod
    def _normalize_uf(cls, value: str | None) -> str | None:
        if not value:
            return value
        return value.strip().upper()[:2]


class ClienteRead(BaseModel):
    """Saída de cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    filial_id: uuid.UUID | None
    person_type: PersonType
    status: ClienteStatus
    nome: str
    nome_fantasia: str | None
    cpf: str | None
    cnpj: str | None
    email: str | None
    telefone: str | None
    celular: str | None
    cidade: str | None
    uf: str | None
    categoria_codigo: str | None
    limite_credito: Decimal
    blacklist: bool
    created_at: datetime
