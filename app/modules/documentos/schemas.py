"""Schemas Pydantic do motor de PDF."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.shared.enums import DocFamilia, DocGeradoStatus


class DocumentoGeradoRead(BaseModel):
    id: uuid.UUID
    template_id: str
    titulo: str
    familia: DocFamilia
    entidade_tipo: str | None
    entidade_id: uuid.UUID | None
    status: DocGeradoStatus
    storage_key: str | None
    content_type: str
    tamanho_bytes: int | None
    hash_sha256: str | None
    watermark: str | None
    erro_mensagem: str | None
    concluido_em: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GerarPdfRequest(BaseModel):
    template_id: str
    entidade_id: uuid.UUID
    filial_id: uuid.UUID | None = None
    sincrono: bool | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
