"""Modelos ORM do módulo Parâmetros (§14.5)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel


class ParametroSistema(TenantBaseModel):
    """Override de parâmetro por tenant ou filial."""

    __tablename__ = "parametros_sistema"
    __table_args__ = (
        Index(
            "uq_parametros_tenant_chave",
            "tenant_id",
            "chave",
            unique=True,
            postgresql_where=text("filial_id IS NULL AND deleted_at IS NULL"),
        ),
        Index(
            "uq_parametros_filial_chave",
            "tenant_id",
            "filial_id",
            "chave",
            unique=True,
            postgresql_where=text("filial_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("ix_parametros_sistema_tenant", "tenant_id"),
    )

    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chave: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
