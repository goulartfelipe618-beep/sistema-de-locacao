"""Schemas Pydantic do módulo Relatórios."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.shared.enums import RelCategoria, RelEmissaoStatus, RelFormato, RelRecorrencia


class EmissaoCreate(BaseModel):
    categoria: RelCategoria
    relatorio_codigo: str = Field(min_length=1, max_length=60)
    formato: RelFormato = RelFormato.PDF
    parametros: dict[str, Any] = Field(default_factory=dict)
    usar_cache: bool = True
    colunas: list[str] | None = None


class EmissaoRead(BaseModel):
    id: uuid.UUID
    categoria: RelCategoria
    relatorio_codigo: str
    titulo: str
    formato: RelFormato
    status: RelEmissaoStatus
    pesado: bool
    linhas_count: int | None
    erro_mensagem: str | None
    iniciado_em: datetime | None
    concluido_em: datetime | None
    cache_valido_ate: datetime | None

    model_config = {"from_attributes": True}


class AgendamentoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    categoria: RelCategoria
    relatorio_codigo: str
    formato: RelFormato = RelFormato.PDF
    parametros: dict[str, Any] = Field(default_factory=dict)
    recorrencia: RelRecorrencia
    hora_execucao: str = "08:00"
    dia_semana: int | None = None
    dia_mes: int | None = None
    email_destinatarios: str | None = None


class AgendamentoRead(BaseModel):
    id: uuid.UUID
    nome: str
    categoria: RelCategoria
    relatorio_codigo: str
    formato: RelFormato
    recorrencia: RelRecorrencia
    ativo: bool
    proxima_execucao_em: datetime | None
    ultima_execucao_em: datetime | None

    model_config = {"from_attributes": True}
