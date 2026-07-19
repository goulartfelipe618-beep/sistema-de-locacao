"""Documentos anexados ao cadastro de clientes.

Revision ID: 0026_cliente_documentos
Revises: 0025_cliente_cnh
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_cliente_documentos"
down_revision: str | None = "0025_cliente_cnh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_documentos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("cliente_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("inline_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cliente_documentos_cliente_id", "cliente_documentos", ["cliente_id"])
    op.create_index("ix_cliente_documentos_tenant_id", "cliente_documentos", ["tenant_id"])
    op.create_index(
        "uq_cliente_documentos_tenant_cliente_tipo_active",
        "cliente_documentos",
        ["tenant_id", "cliente_id", "tipo"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_cliente_documentos_tenant_cliente_tipo_active", table_name="cliente_documentos")
    op.drop_index("ix_cliente_documentos_tenant_id", table_name="cliente_documentos")
    op.drop_index("ix_cliente_documentos_cliente_id", table_name="cliente_documentos")
    op.drop_table("cliente_documentos")
