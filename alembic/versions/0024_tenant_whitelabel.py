"""White label: identidade do sistema, endereço e onboarding obrigatório.

Revision ID: 0024_tenant_whitelabel
Revises: 0023_intermediacao
Create Date: 2026-07-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_tenant_whitelabel"
down_revision: str | None = "0023_intermediacao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("app_display_name", sa.String(200), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("setup_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("tenants", sa.Column("ie", sa.String(20), nullable=True))
    op.add_column("tenants", sa.Column("website", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("document_footer_text", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("zip_code", sa.String(8), nullable=True))
    op.add_column("tenants", sa.Column("address", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("number", sa.String(20), nullable=True))
    op.add_column("tenants", sa.Column("complement", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("district", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("state", sa.String(2), nullable=True))

    op.alter_column(
        "tenants",
        "logo_url",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )

    # Tenants já configurados antes desta migration não precisam refazer onboarding.
    op.execute(
        """
        UPDATE tenants
        SET setup_completed_at = NOW() AT TIME ZONE 'UTC'
        WHERE setup_completed_at IS NULL
          AND deleted_at IS NULL
          AND cnpj IS NOT NULL
          AND email IS NOT NULL
          AND phone IS NOT NULL
          AND legal_name IS NOT NULL
        """
    )


def downgrade() -> None:
    op.alter_column(
        "tenants",
        "logo_url",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.drop_column("tenants", "state")
    op.drop_column("tenants", "city")
    op.drop_column("tenants", "district")
    op.drop_column("tenants", "complement")
    op.drop_column("tenants", "number")
    op.drop_column("tenants", "address")
    op.drop_column("tenants", "zip_code")
    op.drop_column("tenants", "document_footer_text")
    op.drop_column("tenants", "website")
    op.drop_column("tenants", "ie")
    op.drop_column("tenants", "setup_completed_at")
    op.drop_column("tenants", "app_display_name")
