"""Garante colunas de foto de veículo (idempotente para deploys parciais).

Revision ID: 0034_veiculo_foto_fix
Revises: 0033_veiculo_foto_capa
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0034_veiculo_foto_fix"
down_revision: str | None = "0033_veiculo_foto_capa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE frota_veiculo_fotos "
        "ADD COLUMN IF NOT EXISTS content_type VARCHAR(120)"
    )
    op.execute(
        "ALTER TABLE frota_veiculo_fotos ADD COLUMN IF NOT EXISTS inline_data TEXT"
    )
    op.execute(
        "ALTER TABLE frota_veiculos "
        "ADD COLUMN IF NOT EXISTS foto_capa_storage_key VARCHAR(500)"
    )
    op.execute(
        "ALTER TABLE frota_veiculos "
        "ADD COLUMN IF NOT EXISTS foto_capa_content_type VARCHAR(120)"
    )
    op.execute(
        "ALTER TABLE frota_veiculos "
        "ADD COLUMN IF NOT EXISTS foto_capa_inline_data TEXT"
    )
    op.execute(
        "ALTER TABLE tenants "
        "ADD COLUMN IF NOT EXISTS site_atendimento_webhook_token VARCHAR(64)"
    )


def downgrade() -> None:
    pass
