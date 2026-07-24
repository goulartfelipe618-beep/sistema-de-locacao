"""Seção Grupos de Carros na home (imagem + textos + CTA).

Revision ID: 0040_site_groups_promo
Revises: 0039_site_showcase_copy
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_site_groups_promo"
down_revision: str | None = "0039_site_showcase_copy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("site_groups_promo_storage_key", sa.String(500), nullable=True))
    op.add_column("tenants", sa.Column("site_groups_promo_content_type", sa.String(120), nullable=True))
    op.add_column("tenants", sa.Column("site_groups_promo_url", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("site_groups_promo_titulo", sa.String(200), nullable=True))
    op.add_column("tenants", sa.Column("site_groups_promo_subtitulo", sa.String(300), nullable=True))
    op.add_column("tenants", sa.Column("site_groups_promo_texto", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("site_groups_promo_cta_texto", sa.String(120), nullable=True))
    op.add_column("tenants", sa.Column("site_groups_promo_cta_url", sa.String(500), nullable=True))
    op.add_column(
        "tenants",
        sa.Column(
            "site_groups_promo_cta_target",
            sa.String(10),
            nullable=False,
            server_default="_self",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "site_groups_promo_cta_target")
    op.drop_column("tenants", "site_groups_promo_cta_url")
    op.drop_column("tenants", "site_groups_promo_cta_texto")
    op.drop_column("tenants", "site_groups_promo_texto")
    op.drop_column("tenants", "site_groups_promo_subtitulo")
    op.drop_column("tenants", "site_groups_promo_titulo")
    op.drop_column("tenants", "site_groups_promo_url")
    op.drop_column("tenants", "site_groups_promo_content_type")
    op.drop_column("tenants", "site_groups_promo_storage_key")
