"""Capa de categoria (imagem do grupo no site).

Revision ID: 0035_categoria_capa
Revises: 0034_veiculo_foto_fix
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_categoria_capa"
down_revision: str | None = "0034_veiculo_foto_fix"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("frota_categorias", sa.Column("capa_storage_key", sa.String(500), nullable=True))
    op.add_column("frota_categorias", sa.Column("capa_content_type", sa.String(120), nullable=True))
    op.add_column("frota_categorias", sa.Column("capa_inline_data", sa.Text(), nullable=True))

    conn = op.get_bind()
    mapping = (
        ("sedan", "A"),
        ("compacto", "B"),
        ("economico", "C"),
        ("suv", "D"),
        ("executivo", "E"),
        ("utilitario", "F"),
        ("blindado", "G"),
    )
    for nome, letra in mapping:
        conn.execute(
            sa.text(
                "UPDATE frota_categorias SET grupo_tarifario = :letra "
                "WHERE lower(nome) = :nome AND (grupo_tarifario IS NULL OR grupo_tarifario = '')"
            ),
            {"nome": nome, "letra": letra},
        )


def downgrade() -> None:
    op.drop_column("frota_categorias", "capa_inline_data")
    op.drop_column("frota_categorias", "capa_content_type")
    op.drop_column("frota_categorias", "capa_storage_key")
