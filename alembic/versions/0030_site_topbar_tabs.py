"""Cores das abas da topbar do site.

Revision ID: 0030_site_topbar_tabs
Revises: 0029_site_theme_extended
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_site_topbar_tabs"
down_revision: str | None = "0029_site_theme_extended"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "site_topbar_tab_bg_color",
    "site_topbar_tab_text_color",
    "site_topbar_tab_active_bg_color",
    "site_topbar_tab_active_text_color",
)


def upgrade() -> None:
    for name in _COLUMNS:
        op.add_column("tenants", sa.Column(name, sa.String(7), nullable=True))


def downgrade() -> None:
    for name in reversed(_COLUMNS):
        op.drop_column("tenants", name)
