"""Slides do carrossel do site institucional.

Revision ID: 0027_site_slides
Revises: 0026_cliente_documentos
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_site_slides"
down_revision: str | None = "0026_cliente_documentos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "int_site_slides",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("titulo", sa.String(200), nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(120), server_default="image/jpeg", nullable=False),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_int_site_slides_tenant_ordem", "int_site_slides", ["tenant_id", "sort_order"])
    op.execute("ALTER TABLE int_site_slides ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE int_site_slides FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON int_site_slides
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_int_site_slides_tenant_ordem", table_name="int_site_slides")
    op.drop_table("int_site_slides")
