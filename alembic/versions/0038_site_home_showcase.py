"""Vitrine da home do site (3 imagens).

Revision ID: 0038_site_home_showcase
Revises: 0037_site_page_transition
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_site_home_showcase"
down_revision: str | None = "0037_site_page_transition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IMAGE_COLUMNS = (
    ("site_showcase_1_storage_key", "site_showcase_1_content_type", "site_showcase_1_url"),
    ("site_showcase_2_storage_key", "site_showcase_2_content_type", "site_showcase_2_url"),
    ("site_showcase_3_storage_key", "site_showcase_3_content_type", "site_showcase_3_url"),
)


def upgrade() -> None:
    for storage_key, content_type, url in _IMAGE_COLUMNS:
        op.add_column("tenants", sa.Column(storage_key, sa.String(500), nullable=True))
        op.add_column("tenants", sa.Column(content_type, sa.String(120), nullable=True))
        op.add_column("tenants", sa.Column(url, sa.Text(), nullable=True))


def downgrade() -> None:
    for storage_key, content_type, url in reversed(_IMAGE_COLUMNS):
        op.drop_column("tenants", url)
        op.drop_column("tenants", content_type)
        op.drop_column("tenants", storage_key)
