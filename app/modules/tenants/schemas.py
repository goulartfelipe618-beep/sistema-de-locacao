"""Schemas Pydantic do módulo de Empresas/Filiais."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.enums import FilialStatus, TenantStatus
from app.shared.value_objects import is_valid_cnpj, only_digits


class TenantRead(BaseModel):
    """Representação de saída de uma empresa (tenant)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    legal_name: str
    trade_name: str | None
    cnpj: str | None
    status: TenantStatus
    plan: str
    email: str | None
    phone: str | None
    logo_storage_key: str | None = None
    logo_url: str | None = None
    brand_primary_color: str | None = None
    cert_a1_valid_until: date | None = None
    cert_a1_subject: str | None = None
    cert_configured: bool = False
    created_at: datetime


class TenantUpdate(BaseModel):
    """Dados editáveis da empresa (tenant)."""

    legal_name: str | None = Field(default=None, min_length=2, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    logo_storage_key: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    brand_primary_color: str | None = Field(default=None, max_length=7)

    @field_validator("brand_primary_color")
    @classmethod
    def _validate_color(cls, value: str | None) -> str | None:
        if not value:
            return None
        color = value.strip()
        if not color.startswith("#") or len(color) not in (4, 7):
            raise ValueError("Cor deve ser hexadecimal (#RGB ou #RRGGBB).")
        return color


class FilialBase(BaseModel):
    """Campos comuns de filial."""

    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=200)
    cnpj: str | None = Field(default=None, max_length=18)
    status: FilialStatus = FilialStatus.ACTIVE
    is_headquarters: bool = False
    zip_code: str | None = Field(default=None, max_length=9)
    address: str | None = Field(default=None, max_length=255)
    number: str | None = Field(default=None, max_length=20)
    complement: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("cnpj")
    @classmethod
    def _validate_cnpj(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = only_digits(value)
        if not is_valid_cnpj(digits):
            raise ValueError("CNPJ inválido.")
        return digits


class FilialCreate(FilialBase):
    """Dados para criação de filial."""


class FilialUpdate(BaseModel):
    """Dados para atualização de filial (parcial)."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    status: FilialStatus | None = None
    is_headquarters: bool | None = None
    zip_code: str | None = Field(default=None, max_length=9)
    address: str | None = Field(default=None, max_length=255)
    number: str | None = Field(default=None, max_length=20)
    complement: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    phone: str | None = Field(default=None, max_length=20)


class FilialRead(BaseModel):
    """Representação de saída de uma filial."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    cnpj: str | None
    status: FilialStatus
    is_headquarters: bool
    city: str | None
    state: str | None
    created_at: datetime
