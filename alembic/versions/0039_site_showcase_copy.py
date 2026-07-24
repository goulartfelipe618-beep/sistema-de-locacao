"""Vitrine da home — título, descrição e CTA por imagem.

Revision ID: 0039_site_showcase_copy
Revises: 0038_site_home_showcase
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_site_showcase_copy"
down_revision: str | None = "0038_site_home_showcase"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_META_SUFFIXES = ("titulo", "descricao", "cta_texto", "cta_url", "cta_target")


def upgrade() -> None:
    for slot in (1, 2, 3):
        op.add_column(
            "tenants",
            sa.Column(f"site_showcase_{slot}_titulo", sa.String(200), nullable=True),
        )
        op.add_column(
            "tenants",
            sa.Column(f"site_showcase_{slot}_descricao", sa.Text(), nullable=True),
        )
        op.add_column(
            "tenants",
            sa.Column(f"site_showcase_{slot}_cta_texto", sa.String(120), nullable=True),
        )
        op.add_column(
            "tenants",
            sa.Column(f"site_showcase_{slot}_cta_url", sa.String(500), nullable=True),
        )
        op.add_column(
            "tenants",
            sa.Column(
                f"site_showcase_{slot}_cta_target",
                sa.String(10),
                nullable=False,
                server_default="_self",
            ),
        )


def downgrade() -> None:
    for slot in (3, 2, 1):
        for suffix in reversed(_META_SUFFIXES):
            op.drop_column("tenants", f"site_showcase_{slot}_{suffix}")
