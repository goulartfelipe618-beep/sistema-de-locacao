"""Modelos ORM do módulo Relatórios (§11)."""

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
    LargeBinary,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import RelCategoria, RelEmissaoStatus, RelFormato, RelRecorrencia


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class RelEmissao(TenantBaseModel):
    """Histórico de emissões de relatórios (§11 — cache e re-download)."""

    __tablename__ = "rel_emissoes"
    __table_args__ = (
        Index("ix_rel_emissoes_tenant_status", "tenant_id", "status"),
        Index("ix_rel_emissoes_tenant_categoria", "tenant_id", "categoria"),
        Index("ix_rel_emissoes_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    categoria: Mapped[RelCategoria] = mapped_column(
        _str_enum(RelCategoria, "rel_categoria", 15),
        nullable=False,
    )
    relatorio_codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    parametros_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    formato: Mapped[RelFormato] = mapped_column(
        _str_enum(RelFormato, "rel_formato", 10),
        nullable=False,
    )
    status: Mapped[RelEmissaoStatus] = mapped_column(
        _str_enum(RelEmissaoStatus, "rel_emissao_status", 15),
        nullable=False,
        default=RelEmissaoStatus.PENDENTE,
    )
    pesado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    conteudo_inline: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamanho_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    iniciado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    concluido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cache_valido_ate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    linhas_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RelAgendamento(TenantBaseModel):
    """Agendamento recorrente de relatório (§11)."""

    __tablename__ = "rel_agendamentos"
    __table_args__ = (
        Index("ix_rel_agendamentos_tenant_ativo", "tenant_id", "ativo"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria: Mapped[RelCategoria] = mapped_column(
        _str_enum(RelCategoria, "rel_agend_categoria", 15),
        nullable=False,
    )
    relatorio_codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    parametros_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    formato: Mapped[RelFormato] = mapped_column(
        _str_enum(RelFormato, "rel_agend_formato", 10),
        nullable=False,
        default=RelFormato.PDF,
    )
    recorrencia: Mapped[RelRecorrencia] = mapped_column(
        _str_enum(RelRecorrencia, "rel_recorrencia", 10),
        nullable=False,
    )
    hora_execucao: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00")
    dia_semana: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dia_mes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email_destinatarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultima_execucao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    proxima_execucao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultima_emissao_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("rel_emissoes.id", ondelete="SET NULL"),
        nullable=True,
    )
