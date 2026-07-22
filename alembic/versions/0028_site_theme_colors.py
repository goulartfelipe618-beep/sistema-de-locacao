"""Cores do site público no tenant (white-label).

Revision ID: 0028_site_theme_colors
Revises: 0027_site_slides
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_site_theme_colors"
down_revision: str | None = "0027_site_slides"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("site_primary_color", sa.String(7), nullable=True))
    op.add_column("tenants", sa.Column("site_background_color", sa.String(7), nullable=True))
    op.add_column("tenants", sa.Column("site_text_color", sa.String(7), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "site_text_color")
    op.drop_column("tenants", "site_background_color")
    op.drop_column("tenants", "site_primary_color")
