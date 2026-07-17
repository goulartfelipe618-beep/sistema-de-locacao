"""Schemas Pydantic do módulo de Identidade (contratos de entrada/saída)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.config import settings


class LoginRequest(BaseModel):
    """Credenciais de autenticação."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Login2FARequest(BaseModel):
    """Segundo fator após senha válida (API)."""

    pending_token: str
    code: str = Field(min_length=6, max_length=12)


class AuthLoginResponse(BaseModel):
    """Resposta de login: tokens ou desafio 2FA."""

    requires_2fa: bool = False
    pending_token: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None


class TwoFactorDisableRequest(BaseModel):
    """Desativação de 2FA."""

    password: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=6, max_length=12)


class TwoFactorConfirmRequest(BaseModel):
    """Confirmação de setup 2FA."""

    code: str = Field(min_length=6, max_length=6)


class TwoFactorSetupResponse(BaseModel):
    """QR Code e URI para configurar autenticador."""

    provisioning_uri: str
    qr_data_uri: str


class TwoFactorStatusResponse(BaseModel):
    """Status do 2FA do usuário atual."""

    enabled: bool
    enabled_at: datetime | None = None
    recovery_codes_remaining: int = 0


class TokenPair(BaseModel):
    """Par de tokens emitido pela API REST."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = settings.access_token_expire_minutes * 60


class RefreshRequest(BaseModel):
    """Solicitação de renovação de token de acesso."""

    refresh_token: str


class PermissionRead(BaseModel):
    """Representação de uma permissão."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    module: str
    resource: str
    action: str
    description: str


class RoleRead(BaseModel):
    """Representação de um papel."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    is_system: bool


class RoleCreate(BaseModel):
    """Dados para criação de papel personalizado."""

    slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    permission_ids: list[uuid.UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Dados para atualização de papel e permissões."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    permission_ids: list[uuid.UUID] | None = None


class UserBase(BaseModel):
    """Campos comuns de usuário."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    is_active: bool = True


class UserCreate(UserBase):
    """Dados para criação de usuário."""

    password: str = Field(min_length=settings.password_min_length, max_length=128)
    role_ids: list[uuid.UUID] = Field(default_factory=list)
    filial_ids: list[uuid.UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Dados para atualização de usuário (todos opcionais)."""

    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None
    password: str | None = Field(
        default=None, min_length=settings.password_min_length, max_length=128
    )
    role_ids: list[uuid.UUID] | None = None
    filial_ids: list[uuid.UUID] | None = None


class UserRead(BaseModel):
    """Representação de saída de um usuário."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None
    totp_enabled: bool = False
    created_at: datetime


class CurrentUserRead(BaseModel):
    """Usuário atual com papéis e permissões resolvidas (endpoint ``/auth/me``)."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: list[str]
    permissions: list[str]
    totp_enabled: bool = False
