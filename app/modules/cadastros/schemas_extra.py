"""Schemas dos cadastros complementares."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.enums import (
    CadastroStatus,
    MotoristaCnhStatus,
    MotoristaVinculo,
    ParceiroTipo,
    PersonType,
)
from app.shared.value_objects import is_valid_cnpj, is_valid_cpf, only_digits


class MotoristaCreate(BaseModel):
    vinculo: MotoristaVinculo = MotoristaVinculo.TERCEIRO
    status: CadastroStatus = CadastroStatus.ACTIVE
    nome: str = Field(min_length=2, max_length=200)
    cpf: str | None = None
    cliente_id: uuid.UUID | None = None
    data_nascimento: date | None = None
    email: str | None = None
    telefone: str | None = None
    celular: str | None = None
    cnh_numero: str | None = None
    cnh_categoria: str | None = None
    cnh_emissao: date | None = None
    cnh_validade: date | None = None
    cnh_orgao: str | None = None
    cnh_status: MotoristaCnhStatus = MotoristaCnhStatus.REGULAR
    cnh_pontuacao: int | None = Field(default=None, ge=0, le=40)
    observacoes: str | None = None

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        if not is_valid_cpf(digits):
            raise ValueError("CPF inválido.")
        return digits

    @model_validator(mode="after")
    def _vinculo_cliente(self) -> MotoristaCreate:
        if self.vinculo == MotoristaVinculo.CLIENTE and self.cliente_id is None:
            raise ValueError("Informe o cliente quando o vínculo for Cliente.")
        return self


class MotoristaUpdate(BaseModel):
    vinculo: MotoristaVinculo | None = None
    status: CadastroStatus | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    cliente_id: uuid.UUID | None = None
    data_nascimento: date | None = None
    email: str | None = None
    telefone: str | None = None
    celular: str | None = None
    cnh_numero: str | None = None
    cnh_categoria: str | None = None
    cnh_emissao: date | None = None
    cnh_validade: date | None = None
    cnh_orgao: str | None = None
    cnh_status: MotoristaCnhStatus | None = None
    cnh_pontuacao: int | None = Field(default=None, ge=0, le=40)
    observacoes: str | None = None


class MotoristaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cliente_id: uuid.UUID | None
    vinculo: MotoristaVinculo
    status: CadastroStatus
    nome: str
    cpf: str | None
    cnh_numero: str | None
    cnh_categoria: str | None
    cnh_validade: date | None
    cnh_status: MotoristaCnhStatus
    email: str | None
    celular: str | None
    created_at: datetime


class ParceiroCreate(BaseModel):
    person_type: PersonType
    tipo: ParceiroTipo = ParceiroTipo.INDICACAO
    status: CadastroStatus = CadastroStatus.ACTIVE
    nome: str = Field(min_length=2, max_length=200)
    nome_fantasia: str | None = None
    cpf: str | None = None
    cnpj: str | None = None
    email: str | None = None
    telefone: str | None = None
    comissao_percentual: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    comissao_valor_fixo: Decimal = Field(default=Decimal("0"), ge=0)
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    pix_chave: str | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    observacoes: str | None = None

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        if not is_valid_cpf(digits):
            raise ValueError("CPF inválido.")
        return digits

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        if not is_valid_cnpj(digits):
            raise ValueError("CNPJ inválido.")
        return digits

    @model_validator(mode="after")
    def _doc(self) -> ParceiroCreate:
        if self.person_type == PersonType.NATURAL and not self.cpf:
            raise ValueError("CPF é obrigatório para PF.")
        if self.person_type == PersonType.LEGAL and not self.cnpj:
            raise ValueError("CNPJ é obrigatório para PJ.")
        if self.person_type == PersonType.NATURAL:
            self.cnpj = None
        else:
            self.cpf = None
        return self


class ParceiroUpdate(BaseModel):
    tipo: ParceiroTipo | None = None
    status: CadastroStatus | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    nome_fantasia: str | None = None
    email: str | None = None
    telefone: str | None = None
    comissao_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    comissao_valor_fixo: Decimal | None = Field(default=None, ge=0)
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    pix_chave: str | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    observacoes: str | None = None


class ParceiroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    person_type: PersonType
    tipo: ParceiroTipo
    status: CadastroStatus
    nome: str
    cpf: str | None
    cnpj: str | None
    email: str | None
    comissao_percentual: Decimal
    created_at: datetime


class FornecedorCreate(BaseModel):
    status: CadastroStatus = CadastroStatus.ACTIVE
    nome: str = Field(min_length=2, max_length=200)
    nome_fantasia: str | None = None
    cnpj: str | None = None
    ie: str | None = None
    categoria_codigo: str | None = None
    email: str | None = None
    telefone: str | None = None
    celular: str | None = None
    cep: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    pix_chave: str | None = None
    prazo_pagamento_dias: int = Field(default=30, ge=0, le=365)
    desconto_percentual: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    rating: int | None = Field(default=None, ge=1, le=5)
    observacoes: str | None = None

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        if not is_valid_cnpj(digits):
            raise ValueError("CNPJ inválido.")
        return digits

    @field_validator("cep")
    @classmethod
    def _cep(cls, value: str | None) -> str | None:
        if not value:
            return None
        return only_digits(value)[:8]

    @field_validator("uf")
    @classmethod
    def _uf(cls, value: str | None) -> str | None:
        return value.strip().upper()[:2] if value else None


class FornecedorUpdate(BaseModel):
    status: CadastroStatus | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    nome_fantasia: str | None = None
    ie: str | None = None
    categoria_codigo: str | None = None
    email: str | None = None
    telefone: str | None = None
    celular: str | None = None
    cep: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    pix_chave: str | None = None
    prazo_pagamento_dias: int | None = Field(default=None, ge=0, le=365)
    desconto_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    rating: int | None = Field(default=None, ge=1, le=5)
    bloqueado: bool | None = None
    motivo_bloqueio: str | None = None
    observacoes: str | None = None


class FornecedorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    status: CadastroStatus
    nome: str
    cnpj: str | None
    categoria_codigo: str | None
    email: str | None
    cidade: str | None
    uf: str | None
    bloqueado: bool
    created_at: datetime


class VendedorCreate(BaseModel):
    status: CadastroStatus = CadastroStatus.ACTIVE
    nome: str = Field(min_length=2, max_length=200)
    email: str | None = None
    telefone: str | None = None
    usuario_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    meta_contratos_mes: int = Field(default=0, ge=0)
    meta_faturamento_mes: Decimal = Field(default=Decimal("0"), ge=0)
    comissao_percentual: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    observacoes: str | None = None


class VendedorUpdate(BaseModel):
    status: CadastroStatus | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    email: str | None = None
    telefone: str | None = None
    usuario_id: uuid.UUID | None = None
    filial_id: uuid.UUID | None = None
    meta_contratos_mes: int | None = Field(default=None, ge=0)
    meta_faturamento_mes: Decimal | None = Field(default=None, ge=0)
    comissao_percentual: Decimal | None = Field(default=None, ge=0, le=100)
    observacoes: str | None = None


class VendedorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID | None
    filial_id: uuid.UUID | None
    status: CadastroStatus
    nome: str
    email: str | None
    meta_contratos_mes: int
    meta_faturamento_mes: Decimal
    comissao_percentual: Decimal
    created_at: datetime
