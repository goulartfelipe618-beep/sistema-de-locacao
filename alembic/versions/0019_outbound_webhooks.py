"""Webhooks outbound da API pública (§12.5).

Revision ID: 0019_outbound_webhooks
Revises: 0018_tenant_branding
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_outbound_webhooks"
down_revision: str | None = "0018_tenant_branding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "int_outbound_webhooks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("filial_id", sa.UUID(), nullable=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("eventos_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("secret_cripto", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ultimo_disparo_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_erro", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["filial_id"], ["filiais.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_int_outbound_tenant", "int_outbound_webhooks", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_int_outbound_tenant", table_name="int_outbound_webhooks")
    op.drop_table("int_outbound_webhooks")
