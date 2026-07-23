"""Campos para fotos de veículo sem R2 (inline).

Revision ID: 0032_veiculo_foto_inline
Revises: 0031_site_atendimento_webhook
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_veiculo_foto_inline"
down_revision: str | None = "0031_site_atendimento_webhook"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("frota_veiculo_fotos", sa.Column("content_type", sa.String(120), nullable=True))
    op.add_column("frota_veiculo_fotos", sa.Column("inline_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("frota_veiculo_fotos", "inline_data")
    op.drop_column("frota_veiculo_fotos", "content_type")
