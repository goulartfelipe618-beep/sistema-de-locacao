"""Integrações: conectores, webhooks, consultas e API Keys (§12).

Revision ID: 0014_integracoes
Revises: 0013_relatorios
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_integracoes"
down_revision: str | None = "0013_relatorios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "int_provedor_configs",
    "int_webhook_eventos",
    "int_consultas",
    "int_api_keys",
)


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _tenant() -> sa.Column:
    return sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False)


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "int_provedor_configs",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("provedor", sa.String(60), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("credenciais_cripto", sa.Text(), nullable=True),
        sa.Column("webhook_secret_cripto", sa.Text(), nullable=True),
        sa.Column("webhook_token", sa.String(64), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(10), nullable=False, server_default="ativo"),
        sa.Column("ultimo_sync_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_erro", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["filial_id"], ["filiais.id"], name="fk_int_prov_cfg_filial_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_int_provedor_configs"),
    )
    op.create_index("ix_int_prov_cfg_tenant_tipo", "int_provedor_configs", ["tenant_id", "tipo"])
    op.create_index("ix_int_prov_cfg_webhook_token", "int_provedor_configs", ["webhook_token"], unique=True)

    op.create_table(
        "int_webhook_eventos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provedor", sa.String(60), nullable=False),
        sa.Column("evento_tipo", sa.String(60), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("assinatura_valida", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(12), nullable=False, server_default="recebido"),
        sa.Column("processado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["config_id"], ["int_provedor_configs.id"], name="fk_int_webhook_cfg_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_int_webhook_eventos"),
    )
    op.create_index("ix_int_webhook_tenant_status", "int_webhook_eventos", ["tenant_id", "status"])

    op.create_table(
        "int_consultas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("referencia_tipo", sa.String(40), nullable=True),
        sa.Column("referencia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="sucesso"),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["config_id"], ["int_provedor_configs.id"], name="fk_int_consulta_cfg_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_int_consultas"),
    )
    op.create_index("ix_int_consultas_tenant_tipo", "int_consultas", ["tenant_id", "tipo"])

    op.create_table(
        "int_api_keys",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rate_limit_por_minuto", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_uso_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_por_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["criado_por_id"], ["users.id"], name="fk_int_api_key_user_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_int_api_keys"),
    )
    op.create_index("ix_int_api_keys_prefix", "int_api_keys", ["key_prefix"])

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.drop_table(table)
