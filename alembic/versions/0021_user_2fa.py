"""Autenticação 2FA opcional (TOTP) para usuários (§14.3).

Revision ID: 0021_user_2fa
Revises: 0020_notificacoes
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_user_2fa"
down_revision: str | None = "0020_notificacoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("totp_secret_encrypted", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("users", sa.Column("recovery_codes_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "recovery_codes_encrypted")
    op.drop_column("users", "totp_enabled_at")
    op.drop_column("users", "totp_secret_encrypted")
    op.drop_column("users", "totp_enabled")
