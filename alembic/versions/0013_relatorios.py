"""Relatórios: emissões e agendamentos (§11).

Revision ID: 0013_relatorios
Revises: 0012_fiscal
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_relatorios"
down_revision: str | None = "0012_fiscal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("rel_emissoes", "rel_agendamentos")


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
        "rel_emissoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("categoria", sa.String(15), nullable=False),
        sa.Column("relatorio_codigo", sa.String(60), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("parametros_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("formato", sa.String(10), nullable=False),
        sa.Column("status", sa.String(15), nullable=False, server_default="pendente"),
        sa.Column("pesado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("conteudo_inline", sa.LargeBinary(), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=True),
        sa.Column("hash_sha256", sa.String(64), nullable=True),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cache_valido_ate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linhas_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_rel_emissoes_user_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_rel_emissoes"),
    )
    op.create_index("ix_rel_emissoes_tenant_id", "rel_emissoes", ["tenant_id"])
    op.create_index("ix_rel_emissoes_tenant_status", "rel_emissoes", ["tenant_id", "status"])

    op.create_table(
        "rel_agendamentos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("categoria", sa.String(15), nullable=False),
        sa.Column("relatorio_codigo", sa.String(60), nullable=False),
        sa.Column("parametros_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("formato", sa.String(10), nullable=False, server_default="pdf"),
        sa.Column("recorrencia", sa.String(10), nullable=False),
        sa.Column("hora_execucao", sa.String(5), nullable=False, server_default="08:00"),
        sa.Column("dia_semana", sa.Integer(), nullable=True),
        sa.Column("dia_mes", sa.Integer(), nullable=True),
        sa.Column("email_destinatarios", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ultima_execucao_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proxima_execucao_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultima_emissao_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_rel_agend_user_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["ultima_emissao_id"], ["rel_emissoes.id"], name="fk_rel_agend_emissao_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rel_agendamentos"),
    )
    op.create_index("ix_rel_agendamentos_tenant_id", "rel_agendamentos", ["tenant_id"])

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.drop_table(table)
