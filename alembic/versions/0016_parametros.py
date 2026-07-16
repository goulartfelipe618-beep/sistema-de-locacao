"""Parâmetros do sistema (§14.5).

Revision ID: 0016_parametros
Revises: 0015_automacoes
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_parametros"
down_revision: str | None = "0015_automacoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "parametros_sistema",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chave", sa.String(120), nullable=False),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["filial_id"], ["filiais.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_parametros_sistema_tenant", "parametros_sistema", ["tenant_id"])
    op.create_index("ix_parametros_sistema_chave", "parametros_sistema", ["chave"])
    op.create_index("ix_parametros_sistema_filial_id", "parametros_sistema", ["filial_id"])
    op.create_index(
        "uq_parametros_tenant_chave",
        "parametros_sistema",
        ["tenant_id", "chave"],
        unique=True,
        postgresql_where=sa.text("filial_id IS NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "uq_parametros_filial_chave",
        "parametros_sistema",
        ["tenant_id", "filial_id", "chave"],
        unique=True,
        postgresql_where=sa.text("filial_id IS NOT NULL AND deleted_at IS NULL"),
    )
    _enable_rls("parametros_sistema")


def downgrade() -> None:
    op.drop_table("parametros_sistema")
