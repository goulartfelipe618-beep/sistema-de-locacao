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
    app_display_name: str | None = None
    setup_completed_at: datetime | None = None
    ie: str | None = None
    website: str | None = None
    document_footer_text: str | None = None
    zip_code: str | None = None
    address: str | None = None
    number: str | None = None
    complement: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None
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
    logo_url: str | None = Field(default=None)
    brand_primary_color: str | None = Field(default=None, max_length=7)
    site_primary_color: str | None = Field(default=None, max_length=7)
    site_background_color: str | None = Field(default=None, max_length=7)
    site_text_color: str | None = Field(default=None, max_length=7)

    @field_validator("brand_primary_color")
    @classmethod
    def _validate_color(cls, value: str | None) -> str | None:
        if not value:
            return None
        color = value.strip()
        if not color.startswith("#") or len(color) not in (4, 7):
            raise ValueError("Cor deve ser hexadecimal (#RGB ou #RRGGBB).")
        return color


def _optional_hex_color(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    color = stripped
    if not color.startswith("#") or len(color) not in (4, 7):
        raise ValueError("Cor deve ser hexadecimal (#RGB ou #RRGGBB).")
    return color


class SiteThemeUpdate(BaseModel):
    """Cores do site institucional público."""

    site_primary_color: str | None = Field(default=None, max_length=7)
    site_background_color: str | None = Field(default=None, max_length=7)
    site_text_color: str | None = Field(default=None, max_length=7)
    site_header_bg_color: str | None = Field(default=None, max_length=7)
    site_header_text_color: str | None = Field(default=None, max_length=7)
    site_topbar_bg_color: str | None = Field(default=None, max_length=7)
    site_topbar_tab_bg_color: str | None = Field(default=None, max_length=7)
    site_topbar_tab_text_color: str | None = Field(default=None, max_length=7)
    site_topbar_tab_active_bg_color: str | None = Field(default=None, max_length=7)
    site_topbar_tab_active_text_color: str | None = Field(default=None, max_length=7)
    site_button_bg_color: str | None = Field(default=None, max_length=7)
    site_button_text_color: str | None = Field(default=None, max_length=7)
    site_link_color: str | None = Field(default=None, max_length=7)
    site_border_color: str | None = Field(default=None, max_length=7)
    site_surface_color: str | None = Field(default=None, max_length=7)
    site_text_muted_color: str | None = Field(default=None, max_length=7)
    site_footer_bg_color: str | None = Field(default=None, max_length=7)
    site_footer_text_color: str | None = Field(default=None, max_length=7)
    site_transition_enabled: bool = False
    site_transition_bg_color: str | None = Field(default=None, max_length=7)
    site_transition_image_size_px: int | None = Field(default=None, ge=48, le=400)
    remove_transition_image: bool = False
    remove_showcase_image_1: bool = False
    remove_showcase_image_2: bool = False
    remove_showcase_image_3: bool = False
    showcase_1_titulo: str | None = Field(default=None, max_length=200)
    showcase_1_descricao: str | None = Field(default=None, max_length=2000)
    showcase_1_cta_texto: str | None = Field(default=None, max_length=120)
    showcase_1_cta_url: str | None = Field(default=None, max_length=500)
    showcase_1_cta_target: str | None = Field(default="_self", max_length=10)
    showcase_2_titulo: str | None = Field(default=None, max_length=200)
    showcase_2_descricao: str | None = Field(default=None, max_length=2000)
    showcase_2_cta_texto: str | None = Field(default=None, max_length=120)
    showcase_2_cta_url: str | None = Field(default=None, max_length=500)
    showcase_2_cta_target: str | None = Field(default="_self", max_length=10)
    showcase_3_titulo: str | None = Field(default=None, max_length=200)
    showcase_3_descricao: str | None = Field(default=None, max_length=2000)
    showcase_3_cta_texto: str | None = Field(default=None, max_length=120)
    showcase_3_cta_url: str | None = Field(default=None, max_length=500)
    showcase_3_cta_target: str | None = Field(default="_self", max_length=10)
    reset_defaults: bool = False

    @field_validator(
        "site_primary_color",
        "site_background_color",
        "site_text_color",
        "site_header_bg_color",
        "site_header_text_color",
        "site_topbar_bg_color",
        "site_topbar_tab_bg_color",
        "site_topbar_tab_text_color",
        "site_topbar_tab_active_bg_color",
        "site_topbar_tab_active_text_color",
        "site_button_bg_color",
        "site_button_text_color",
        "site_link_color",
        "site_border_color",
        "site_surface_color",
        "site_text_muted_color",
        "site_footer_bg_color",
        "site_footer_text_color",
        "site_transition_bg_color",
    )
    @classmethod
    def _validate_optional_color(cls, value: str | None) -> str | None:
        return _optional_hex_color(value)

    @field_validator(
        "showcase_1_cta_target",
        "showcase_2_cta_target",
        "showcase_3_cta_target",
    )
    @classmethod
    def _validate_showcase_cta_target(cls, value: str | None) -> str:
        if not value or value not in ("_self", "_blank"):
            return "_self"
        return value


class TenantSystemUpdate(BaseModel):
    """Configurações completas do sistema (white label + contato + endereço)."""

    legal_name: str = Field(min_length=2, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    app_display_name: str = Field(min_length=2, max_length=200)
    cnpj: str = Field(min_length=1, max_length=18)
    email: str = Field(min_length=5, max_length=255)
    phone: str = Field(min_length=8, max_length=20)
    ie: str | None = Field(default=None, max_length=20)
    website: str | None = Field(default=None, max_length=255)
    document_footer_text: str | None = Field(default=None, max_length=2000)
    brand_primary_color: str = Field(default="#1e5a8a", max_length=7)
    logo_url: str | None = Field(default=None)
    zip_code: str = Field(min_length=8, max_length=9)
    address: str = Field(min_length=2, max_length=255)
    number: str = Field(min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=2)

    @field_validator("cnpj")
    @classmethod
    def _validate_cnpj(cls, value: str) -> str:
        digits = only_digits(value)
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 dígitos.")
        if not is_valid_cnpj(digits):
            raise ValueError("CNPJ inválido.")
        return digits

    @field_validator("zip_code")
    @classmethod
    def _validate_zip(cls, value: str) -> str:
        digits = only_digits(value)
        if len(digits) != 8:
            raise ValueError("CEP inválido.")
        return digits

    @field_validator("state")
    @classmethod
    def _validate_state(cls, value: str) -> str:
        uf = value.strip().upper()
        if len(uf) != 2:
            raise ValueError("UF inválida.")
        return uf

    @field_validator("brand_primary_color")
    @classmethod
    def _validate_color(cls, value: str) -> str:
        color = value.strip()
        if not color.startswith("#") or len(color) not in (4, 7):
            raise ValueError("Cor deve ser hexadecimal (#RGB ou #RRGGBB).")
        return color

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        digits = only_digits(value)
        if len(digits) < 10:
            raise ValueError("Telefone inválido.")
        return digits


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
