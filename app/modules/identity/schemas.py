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
