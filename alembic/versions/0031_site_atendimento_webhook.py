"""Token de webhook do formulário de atendimento do site.

Revision ID: 0031_site_atendimento_webhook
Revises: 0030_site_topbar_tabs
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_site_atendimento_webhook"
down_revision: str | None = "0030_site_topbar_tabs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("site_atendimento_webhook_token", sa.String(64), nullable=True),
    )
    op.create_index(
        "uq_tenants_atendimento_webhook_token",
        "tenants",
        ["site_atendimento_webhook_token"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND site_atendimento_webhook_token IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_tenants_atendimento_webhook_token", table_name="tenants")
    op.drop_column("tenants", "site_atendimento_webhook_token")
