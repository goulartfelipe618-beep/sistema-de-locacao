"""Schemas Pydantic do módulo Automações."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    AutoAcaoTipo,
    AutoAprovacaoStatus,
    AutoEventoGatilho,
    AutoExecucaoStatus,
    AutoExecucaoTipo,
    AutoWorkflowInstanciaStatus,
    AutoWorkflowTimeoutAcao,
)


class RegraCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    descricao: str | None = None
    evento_gatilho: AutoEventoGatilho
    condicao_json: dict = Field(default_factory=dict)
    acao_tipo: AutoAcaoTipo
    acao_params_json: dict = Field(default_factory=dict)
    prioridade: int = Field(default=100, ge=1, le=9999)
    ativo: bool = True


class RegraUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    descricao: str | None = None
    condicao_json: dict | None = None
    acao_tipo: AutoAcaoTipo | None = None
    acao_params_json: dict | None = None
    prioridade: int | None = Field(default=None, ge=1, le=9999)
    ativo: bool | None = None


class RegraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    descricao: str | None
    evento_gatilho: AutoEventoGatilho
    condicao_json: str
    acao_tipo: AutoAcaoTipo
    acao_params_json: str
    ativo: bool
    prioridade: int
    ultima_execucao_em: datetime | None
    created_at: datetime


class WorkflowEtapaInput(BaseModel):
    ordem: int = Field(ge=1)
    nome: str = Field(min_length=2, max_length=120)
    aprovador_papel_slug: str | None = None
    aprovador_user_id: uuid.UUID | None = None
    sla_horas: int = Field(default=24, ge=1)
    timeout_acao: AutoWorkflowTimeoutAcao = AutoWorkflowTimeoutAcao.ESCALAR


class WorkflowCreate(BaseModel):
    codigo: str = Field(min_length=2, max_length=60)
    nome: str = Field(min_length=2, max_length=120)
    descricao: str | None = None
    etapas: list[WorkflowEtapaInput] = Field(default_factory=list)


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nome: str
    descricao: str | None
    ativo: bool
    created_at: datetime


class WorkflowInstanciaCreate(BaseModel):
    workflow_codigo: str
    entidade_tipo: str
    entidade_id: uuid.UUID
    contexto: dict = Field(default_factory=dict)


class WorkflowDecisaoInput(BaseModel):
    aprovar: bool
    comentario: str | None = None


class ExecucaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: AutoExecucaoTipo
    referencia_codigo: str | None
    evento: str | None
    status: AutoExecucaoStatus
    erro_mensagem: str | None
    duracao_ms: int | None
    iniciado_em: datetime | None
    concluido_em: datetime | None
    created_at: datetime


class BeatJobRead(BaseModel):
    key: str
    nome: str
    descricao: str
    task: str
    schedule: str
    queue: str
