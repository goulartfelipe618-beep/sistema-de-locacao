"""Schemas Pydantic do módulo Integrações."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    IntegracaoConsultaStatus,
    IntegracaoConsultaTipo,
    IntegracaoProvedorStatus,
    IntegracaoTipo,
    WebhookEventoStatus,
)


class ProvedorConfigCreate(BaseModel):
    tipo: IntegracaoTipo
    provedor: str = Field(min_length=2, max_length=60)
    nome: str = Field(min_length=2, max_length=120)
    filial_id: uuid.UUID | None = None
    client_id: str | None = None
    client_secret: str | None = None
    api_key: str | None = None
    webhook_secret: str | None = None
    config_json: dict | None = None


class ProvedorConfigUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    client_id: str | None = None
    client_secret: str | None = None
    api_key: str | None = None
    webhook_secret: str | None = None
    config_json: dict | None = None
    status: IntegracaoProvedorStatus | None = None


class ProvedorConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: IntegracaoTipo
    provedor: str
    nome: str
    filial_id: uuid.UUID | None
    status: IntegracaoProvedorStatus
    webhook_token: str
    ultimo_sync_em: datetime | None
    ultimo_erro: str | None
    created_at: datetime


class ApiKeyCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(default_factory=list)
    rate_limit_por_minuto: int = Field(default=60, ge=1, le=10_000)
    expires_at: datetime | None = None


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    key_prefix: str
    scopes_json: str
    rate_limit_por_minuto: int
    ativo: bool
    expires_at: datetime | None
    ultimo_uso_em: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyRead):
    raw_key: str


class TransitoMultasInput(BaseModel):
    veiculo_id: uuid.UUID
    config_id: uuid.UUID | None = None
    importar: bool = True


class TransitoCnhInput(BaseModel):
    motorista_id: uuid.UUID
    config_id: uuid.UUID | None = None
    atualizar_pontuacao: bool = True


class CreditoConsultaInput(BaseModel):
    cliente_id: uuid.UUID
    config_id: uuid.UUID | None = None


class ConsultaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: IntegracaoConsultaTipo
    status: IntegracaoConsultaStatus
    referencia_tipo: str | None
    referencia_id: uuid.UUID | None
    response_json: str | None
    erro_mensagem: str | None
    created_at: datetime


class WebhookEventoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provedor: str
    evento_tipo: str
    status: WebhookEventoStatus
    assinatura_valida: bool
    processado_em: datetime | None
    erro_mensagem: str | None
    created_at: datetime
