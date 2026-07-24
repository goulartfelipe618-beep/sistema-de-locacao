"""Coordenadas das filiais + token Mapbox do site.

Revision ID: 0041_filial_geo_mapbox
Revises: 0040_site_groups_promo
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_filial_geo_mapbox"
down_revision: str | None = "0040_site_groups_promo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("filiais", sa.Column("latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("filiais", sa.Column("longitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("tenants", sa.Column("site_mapbox_access_token", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "site_mapbox_access_token")
    op.drop_column("filiais", "longitude")
    op.drop_column("filiais", "latitude")
