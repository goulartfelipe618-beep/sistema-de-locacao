"""Interruptor master de emissão fiscal por tenant.

Revision ID: 0036_tenant_fiscal_emissao
Revises: 0035_categoria_capa
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_tenant_fiscal_emissao"
down_revision: str | None = "0035_categoria_capa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "fiscal_emissao_habilitada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("tenants", "fiscal_emissao_habilitada", server_default=None)


def downgrade() -> None:
    op.drop_column("tenants", "fiscal_emissao_habilitada")
