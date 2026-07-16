"""Branding da empresa: logo, cores e certificado A1 (§14.1).

Revision ID: 0018_tenant_branding
Revises: 0017_documentos
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_tenant_branding"
down_revision: str | None = "0017_documentos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("logo_storage_key", sa.String(500), nullable=True))
    op.add_column("tenants", sa.Column("logo_url", sa.String(500), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("brand_primary_color", sa.String(7), nullable=True, server_default="#1e5a8a"),
    )
    op.add_column("tenants", sa.Column("cert_a1_encrypted", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("cert_a1_password_encrypted", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("cert_a1_valid_until", sa.Date(), nullable=True))
    op.add_column("tenants", sa.Column("cert_a1_subject", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "cert_a1_subject")
    op.drop_column("tenants", "cert_a1_valid_until")
    op.drop_column("tenants", "cert_a1_password_encrypted")
    op.drop_column("tenants", "cert_a1_encrypted")
    op.drop_column("tenants", "brand_primary_color")
    op.drop_column("tenants", "logo_url")
    op.drop_column("tenants", "logo_storage_key")
