"""Modelos ORM do motor de PDF (§16)."""

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
from app.shared.enums import DocFamilia, DocGeradoStatus


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class DocumentoGerado(TenantBaseModel):
    """Registro de cada PDF emitido pelo sistema (§16)."""

    __tablename__ = "documentos_gerados"
    __table_args__ = (
        Index("ix_documentos_gerados_tenant_status", "tenant_id", "status"),
        Index("ix_documentos_gerados_tenant_template", "tenant_id", "template_id"),
        Index("ix_documentos_gerados_entidade", "entidade_tipo", "entidade_id"),
        Index("ix_documentos_gerados_user_id", "user_id"),
    )

    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    familia: Mapped[DocFamilia] = mapped_column(
        _str_enum(DocFamilia, "doc_familia", 15),
        nullable=False,
    )
    entidade_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[DocGeradoStatus] = mapped_column(
        _str_enum(DocGeradoStatus, "doc_gerado_status", 15),
        nullable=False,
        default=DocGeradoStatus.PENDENTE,
    )
    sincrono: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    watermark: Mapped[str | None] = mapped_column(String(40), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    conteudo_inline: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/pdf"
    )
    tamanho_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    iniciado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    concluido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
