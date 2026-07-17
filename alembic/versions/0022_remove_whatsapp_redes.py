"""Remove WhatsApp e Redes Sociais do escopo do sistema.

Revision ID: 0022_remove_whatsapp_redes
Revises: 0021_user_2fa
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_remove_whatsapp_redes"
down_revision: str | None = "0021_user_2fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE crm_oportunidades SET origem_lead = 'outro' "
            "WHERE origem_lead = 'redes_sociais'"
        )
    )
    op.execute(
        sa.text("UPDATE crm_campanhas SET canal = 'email' WHERE canal = 'whatsapp'")
    )
    op.execute(
        sa.text("UPDATE notificacao_envios SET canal = 'sms' WHERE canal = 'whatsapp'")
    )
    op.drop_column("clientes", "whatsapp")


def downgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column("whatsapp", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
