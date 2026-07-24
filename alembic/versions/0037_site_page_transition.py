"""Transição de carregamento do site público (imagem + fundo).

Revision ID: 0037_site_page_transition
Revises: 0036_tenant_fiscal_emissao
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_site_page_transition"
down_revision: str | None = "0036_tenant_fiscal_emissao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "site_transition_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("tenants", sa.Column("site_transition_bg_color", sa.String(7), nullable=True))
    op.add_column("tenants", sa.Column("site_transition_image_storage_key", sa.String(500), nullable=True))
    op.add_column("tenants", sa.Column("site_transition_image_content_type", sa.String(120), nullable=True))
    op.add_column("tenants", sa.Column("site_transition_image_url", sa.Text(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column(
            "site_transition_image_size_px",
            sa.Integer(),
            nullable=False,
            server_default="120",
        ),
    )
    op.alter_column("tenants", "site_transition_enabled", server_default=None)
    op.alter_column("tenants", "site_transition_image_size_px", server_default=None)


def downgrade() -> None:
    op.drop_column("tenants", "site_transition_image_size_px")
    op.drop_column("tenants", "site_transition_image_url")
    op.drop_column("tenants", "site_transition_image_content_type")
    op.drop_column("tenants", "site_transition_image_storage_key")
    op.drop_column("tenants", "site_transition_bg_color")
    op.drop_column("tenants", "site_transition_enabled")
