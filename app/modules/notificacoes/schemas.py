"""Schemas Pydantic do módulo Notificações."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import NotificacaoCanal, NotificacaoEnvioStatus


class NotificacaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    titulo: str
    mensagem: str
    link: str | None
    lida: bool
    lida_em: datetime | None
    evento: str | None
    referencia_tipo: str | None
    referencia_id: uuid.UUID | None
    created_at: datetime


class NotificacaoEnvioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notificacao_id: uuid.UUID | None
    canal: NotificacaoCanal
    destino: str
    assunto: str | None
    corpo: str
    status: NotificacaoEnvioStatus
    erro_mensagem: str | None
    enviado_em: datetime | None
    created_at: datetime


class NotificacaoSendInput(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    mensagem: str = Field(min_length=1)
    canais: list[NotificacaoCanal] = Field(default_factory=lambda: [NotificacaoCanal.IN_APP])
    user_id: uuid.UUID | None = None
    email: str | None = None
    telefone: str | None = None
    link: str | None = None
    evento: str | None = None
    referencia_tipo: str | None = None
    referencia_id: uuid.UUID | None = None
    assunto: str | None = None
    async_send: bool = True
