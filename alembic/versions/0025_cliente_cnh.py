"""CNH do condutor unificada no cadastro de clientes.

Revision ID: 0025_cliente_cnh
Revises: 0024_tenant_whitelabel
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_cliente_cnh"
down_revision: str | None = "0024_tenant_whitelabel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("cnh_numero", sa.String(20), nullable=True))
    op.add_column("clientes", sa.Column("cnh_categoria", sa.String(10), nullable=True))
    op.add_column("clientes", sa.Column("cnh_emissao", sa.Date(), nullable=True))
    op.add_column("clientes", sa.Column("cnh_validade", sa.Date(), nullable=True))
    op.add_column("clientes", sa.Column("cnh_orgao", sa.String(60), nullable=True))
    op.add_column(
        "clientes",
        sa.Column(
            "cnh_status",
            sa.String(20),
            nullable=False,
            server_default="regular",
        ),
    )
    op.add_column("clientes", sa.Column("cnh_pontuacao", sa.Integer(), nullable=True))

    op.create_index(
        "uq_clientes_tenant_cnh_active",
        "clientes",
        ["tenant_id", "cnh_numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cnh_numero IS NOT NULL"),
    )

    op.execute(
        """
        UPDATE clientes c
        SET
            cnh_numero = m.cnh_numero,
            cnh_categoria = m.cnh_categoria,
            cnh_emissao = m.cnh_emissao,
            cnh_validade = m.cnh_validade,
            cnh_orgao = m.cnh_orgao,
            cnh_status = m.cnh_status,
            cnh_pontuacao = m.cnh_pontuacao
        FROM motoristas m
        WHERE m.cliente_id = c.id
          AND m.deleted_at IS NULL
          AND c.deleted_at IS NULL
        """
    )

    op.execute(
        """
        UPDATE clientes c
        SET
            cnh_numero = m.cnh_numero,
            cnh_categoria = m.cnh_categoria,
            cnh_emissao = m.cnh_emissao,
            cnh_validade = m.cnh_validade,
            cnh_orgao = m.cnh_orgao,
            cnh_status = m.cnh_status,
            cnh_pontuacao = m.cnh_pontuacao
        FROM motoristas m
        WHERE c.cnh_numero IS NULL
          AND m.cliente_id IS NULL
          AND m.deleted_at IS NULL
          AND c.deleted_at IS NULL
          AND c.cpf IS NOT NULL
          AND m.cpf = c.cpf
          AND c.tenant_id = m.tenant_id
        """
    )


def downgrade() -> None:
    op.drop_index("uq_clientes_tenant_cnh_active", table_name="clientes")
    op.drop_column("clientes", "cnh_pontuacao")
    op.drop_column("clientes", "cnh_status")
    op.drop_column("clientes", "cnh_orgao")
    op.drop_column("clientes", "cnh_validade")
    op.drop_column("clientes", "cnh_emissao")
    op.drop_column("clientes", "cnh_categoria")
    op.drop_column("clientes", "cnh_numero")
