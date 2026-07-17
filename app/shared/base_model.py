"""Base declarativa do SQLAlchemy e mixins comuns a todas as entidades.

Padrões aplicados em todo o ERP:
    * Chave primária UUID (gerada na aplicação, amigável a sharding/SaaS).
    * ``created_at`` / ``updated_at`` automáticos.
    * *Soft delete* (``deleted_at``) para preservar histórico e auditoria.
    * Coluna ``tenant_id`` para isolamento multiempresa (Row-Level Security).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Convenção de nomenclatura para constraints/índices: torna as migrations
# determinísticas e o autogenerate do Alembic estável.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa única para todos os modelos ORM da aplicação."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """Adiciona uma chave primária UUID gerada pela aplicação."""

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Adiciona colunas de auditoria temporal automáticas."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class SoftDeleteMixin:
    """Adiciona *soft delete*: registros são marcados, nunca removidos fisicamente."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        """Indica se o registro está logicamente excluído."""
        return self.deleted_at is not None


class TenantMixin:
    """Adiciona a coluna ``tenant_id`` para isolamento multiempresa (RLS).

    Declarada como *declared_attr* para garantir criação de índice em cada
    tabela concreta que herdar o mixin.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            PgUUID(as_uuid=True),
            nullable=False,
            index=True,
        )


class BaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Modelo base para entidades **globais** (não escopadas por tenant)."""

    __abstract__ = True


class TenantBaseModel(BaseModel, TenantMixin):
    """Modelo base para entidades **multiempresa** (escopadas por tenant/RLS)."""

    __abstract__ = True


class AssociationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Base para tabelas de junção (associação N:N).

    Não usa *soft delete*: vínculos são sempre removidos fisicamente para
    respeitar restrições de unicidade ao religar registros.
    """

    __abstract__ = True
