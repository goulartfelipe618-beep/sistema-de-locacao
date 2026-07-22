"""Cores estendidas do site público.

Revision ID: 0029_site_theme_extended
Revises: 0028_site_theme_colors
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_site_theme_extended"
down_revision: str | None = "0028_site_theme_colors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "site_header_bg_color",
    "site_header_text_color",
    "site_topbar_bg_color",
    "site_button_bg_color",
    "site_button_text_color",
    "site_link_color",
    "site_border_color",
    "site_surface_color",
    "site_text_muted_color",
    "site_footer_bg_color",
    "site_footer_text_color",
)


def upgrade() -> None:
    for name in _COLUMNS:
        op.add_column("tenants", sa.Column(name, sa.String(7), nullable=True))


def downgrade() -> None:
    for name in reversed(_COLUMNS):
        op.drop_column("tenants", name)
