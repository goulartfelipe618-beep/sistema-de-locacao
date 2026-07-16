"""Modelos ORM do módulo Automações (§13)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    AutoAcaoTipo,
    AutoAprovacaoStatus,
    AutoEventoGatilho,
    AutoExecucaoStatus,
    AutoExecucaoTipo,
    AutoWorkflowInstanciaStatus,
    AutoWorkflowTimeoutAcao,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class AutoRegra(TenantBaseModel):
    """Regra configurável condição → ação (§13.1)."""

    __tablename__ = "auto_regras"
    __table_args__ = (Index("ix_auto_regras_tenant_ativo", "tenant_id", "ativo"),)

    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    evento_gatilho: Mapped[AutoEventoGatilho] = mapped_column(
        _str_enum(AutoEventoGatilho, "auto_evento_gatilho", 30),
        nullable=False,
    )
    condicao_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    acao_tipo: Mapped[AutoAcaoTipo] = mapped_column(
        _str_enum(AutoAcaoTipo, "auto_acao_tipo", 20),
        nullable=False,
    )
    acao_params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prioridade: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    ultima_execucao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AutoWorkflow(TenantBaseModel):
    """Definição de workflow com múltiplas etapas (§13.2)."""

    __tablename__ = "auto_workflows"
    __table_args__ = (Index("ix_auto_workflows_tenant_codigo", "tenant_id", "codigo"),)

    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    etapas: Mapped[list[AutoWorkflowEtapa]] = relationship(
        back_populates="workflow",
        order_by="AutoWorkflowEtapa.ordem",
    )


class AutoWorkflowEtapa(TenantBaseModel):
    """Etapa de aprovação dentro de um workflow."""

    __tablename__ = "auto_workflow_etapas"
    __table_args__ = (Index("ix_auto_wf_etapa_workflow_ordem", "workflow_id", "ordem"),)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("auto_workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    aprovador_papel_slug: Mapped[str | None] = mapped_column(String(60), nullable=True)
    aprovador_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sla_horas: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    timeout_acao: Mapped[AutoWorkflowTimeoutAcao] = mapped_column(
        _str_enum(AutoWorkflowTimeoutAcao, "auto_wf_timeout_acao", 15),
        nullable=False,
        default=AutoWorkflowTimeoutAcao.ESCALAR,
    )

    workflow: Mapped[AutoWorkflow] = relationship(back_populates="etapas")


class AutoWorkflowInstancia(TenantBaseModel):
    """Instância em execução de um workflow."""

    __tablename__ = "auto_workflow_instancias"
    __table_args__ = (Index("ix_auto_wf_inst_tenant_status", "tenant_id", "status"),)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("auto_workflows.id", ondelete="RESTRICT"),
        nullable=False,
    )
    etapa_atual_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("auto_workflow_etapas.id", ondelete="SET NULL"),
        nullable=True,
    )
    entidade_tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    entidade_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    status: Mapped[AutoWorkflowInstanciaStatus] = mapped_column(
        _str_enum(AutoWorkflowInstanciaStatus, "auto_wf_inst_status", 15),
        nullable=False,
        default=AutoWorkflowInstanciaStatus.PENDENTE,
    )
    contexto_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    etapa_vence_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutoWorkflowAprovacao(TenantBaseModel):
    """Registro de decisão por etapa."""

    __tablename__ = "auto_workflow_aprovacoes"

    instancia_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("auto_workflow_instancias.id", ondelete="CASCADE"),
        nullable=False,
    )
    etapa_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("auto_workflow_etapas.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[AutoAprovacaoStatus] = mapped_column(
        _str_enum(AutoAprovacaoStatus, "auto_aprovacao_status", 12),
        nullable=False,
        default=AutoAprovacaoStatus.PENDENTE,
    )
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    decidido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutoExecucao(TenantBaseModel):
    """Histórico unificado de execuções (§13.4)."""

    __tablename__ = "auto_execucoes"
    __table_args__ = (
        Index("ix_auto_exec_tenant_tipo", "tenant_id", "tipo"),
        Index("ix_auto_exec_tenant_status", "tenant_id", "status"),
    )

    tipo: Mapped[AutoExecucaoTipo] = mapped_column(
        _str_enum(AutoExecucaoTipo, "auto_execucao_tipo", 12),
        nullable=False,
    )
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    referencia_codigo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    evento: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[AutoExecucaoStatus] = mapped_column(
        _str_enum(AutoExecucaoStatus, "auto_execucao_status", 12),
        nullable=False,
        default=AutoExecucaoStatus.PENDENTE,
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    resultado_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    duracao_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
