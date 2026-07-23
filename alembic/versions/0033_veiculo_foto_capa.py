"""Foto de capa do veículo para exibição no site.

Revision ID: 0033_veiculo_foto_capa
Revises: 0032_veiculo_foto_inline
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_veiculo_foto_capa"
down_revision: str | None = "0032_veiculo_foto_inline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("frota_veiculos", sa.Column("foto_capa_storage_key", sa.String(500), nullable=True))
    op.add_column("frota_veiculos", sa.Column("foto_capa_content_type", sa.String(120), nullable=True))
    op.add_column("frota_veiculos", sa.Column("foto_capa_inline_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("frota_veiculos", "foto_capa_inline_data")
    op.drop_column("frota_veiculos", "foto_capa_content_type")
    op.drop_column("frota_veiculos", "foto_capa_storage_key")
