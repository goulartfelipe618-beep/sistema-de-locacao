"""Modelos ORM do módulo Notificações."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import NotificacaoCanal, NotificacaoEnvioStatus


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class Notificacao(TenantBaseModel):
    """Notificação in-app para usuário do sistema."""

    __tablename__ = "notificacoes"
    __table_args__ = (
        Index("ix_notificacoes_tenant_user", "tenant_id", "user_id"),
        Index("ix_notificacoes_tenant_lida", "tenant_id", "lida"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evento: Mapped[str | None] = mapped_column(String(80), nullable=True)
    referencia_tipo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)


class NotificacaoEnvio(TenantBaseModel):
    """Log de envio por canal externo (e-mail, SMS)."""

    __tablename__ = "notificacao_envios"
    __table_args__ = (Index("ix_notificacao_envios_tenant", "tenant_id"),)

    notificacao_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("notificacoes.id", ondelete="SET NULL"),
        nullable=True,
    )
    canal: Mapped[NotificacaoCanal] = mapped_column(
        _str_enum(NotificacaoCanal, "notificacao_canal", 20),
        nullable=False,
    )
    destino: Mapped[str] = mapped_column(String(255), nullable=False)
    assunto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificacaoEnvioStatus] = mapped_column(
        _str_enum(NotificacaoEnvioStatus, "notificacao_envio_status", 20),
        nullable=False,
        default=NotificacaoEnvioStatus.PENDENTE,
    )
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
