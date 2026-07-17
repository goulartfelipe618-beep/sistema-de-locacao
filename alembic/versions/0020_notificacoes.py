"""Módulo de Notificações (in-app + log de envios e-mail/SMS).

Revision ID: 0020_notificacoes
Revises: 0019_outbound_webhooks
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_notificacoes"
down_revision: str | None = "0019_outbound_webhooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notificacoes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("lida", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("lida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evento", sa.String(80), nullable=True),
        sa.Column("referencia_tipo", sa.String(80), nullable=True),
        sa.Column("referencia_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notificacoes_tenant_user", "notificacoes", ["tenant_id", "user_id"])
    op.create_index("ix_notificacoes_tenant_lida", "notificacoes", ["tenant_id", "lida"])

    op.create_table(
        "notificacao_envios",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("notificacao_id", sa.UUID(), nullable=True),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("destino", sa.String(255), nullable=False),
        sa.Column("assunto", sa.String(255), nullable=True),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notificacao_id"], ["notificacoes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notificacao_envios_tenant", "notificacao_envios", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_notificacao_envios_tenant", table_name="notificacao_envios")
    op.drop_table("notificacao_envios")
    op.drop_index("ix_notificacoes_tenant_lida", table_name="notificacoes")
    op.drop_index("ix_notificacoes_tenant_user", table_name="notificacoes")
    op.drop_table("notificacoes")
