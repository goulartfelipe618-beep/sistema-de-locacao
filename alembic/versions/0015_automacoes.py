"""Automações: regras, workflows, jobs Beat e histórico (§13).

Revision ID: 0015_automacoes
Revises: 0014_integracoes
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_automacoes"
down_revision: str | None = "0014_integracoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "auto_regras",
    "auto_workflows",
    "auto_workflow_etapas",
    "auto_workflow_instancias",
    "auto_workflow_aprovacoes",
    "auto_execucoes",
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
        "auto_regras",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("evento_gatilho", sa.String(30), nullable=False),
        sa.Column("condicao_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("acao_tipo", sa.String(20), nullable=False),
        sa.Column("acao_params_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("prioridade", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("ultima_execucao_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_auto_regras"),
    )
    op.create_index("ix_auto_regras_tenant_ativo", "auto_regras", ["tenant_id", "ativo"])

    op.create_table(
        "auto_workflows",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name="pk_auto_workflows"),
    )
    op.create_index("ix_auto_workflows_tenant_codigo", "auto_workflows", ["tenant_id", "codigo"])

    op.create_table(
        "auto_workflow_etapas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("aprovador_papel_slug", sa.String(60), nullable=True),
        sa.Column("aprovador_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sla_horas", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("timeout_acao", sa.String(15), nullable=False, server_default="escalar"),
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["auto_workflows.id"], name="fk_auto_wf_etapa_wf_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["aprovador_user_id"], ["users.id"], name="fk_auto_wf_etapa_user_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auto_workflow_etapas"),
    )
    op.create_index("ix_auto_wf_etapa_workflow_ordem", "auto_workflow_etapas", ["workflow_id", "ordem"])

    op.create_table(
        "auto_workflow_instancias",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("etapa_atual_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entidade_tipo", sa.String(40), nullable=False),
        sa.Column("entidade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(15), nullable=False, server_default="pendente"),
        sa.Column("contexto_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("etapa_vence_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["auto_workflows.id"], name="fk_auto_wf_inst_wf_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["etapa_atual_id"], ["auto_workflow_etapas.id"], name="fk_auto_wf_inst_etapa_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auto_workflow_instancias"),
    )
    op.create_index("ix_auto_wf_inst_tenant_status", "auto_workflow_instancias", ["tenant_id", "status"])

    op.create_table(
        "auto_workflow_aprovacoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("instancia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("etapa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="pendente"),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("decidido_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["instancia_id"], ["auto_workflow_instancias.id"], name="fk_auto_wf_aprov_inst_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["etapa_id"], ["auto_workflow_etapas.id"], name="fk_auto_wf_aprov_etapa_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_auto_wf_aprov_user_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auto_workflow_aprovacoes"),
    )

    op.create_table(
        "auto_execucoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("referencia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("referencia_codigo", sa.String(120), nullable=True),
        sa.Column("evento", sa.String(60), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="pendente"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("resultado_json", sa.Text(), nullable=True),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("duracao_ms", sa.Integer(), nullable=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_auto_execucoes"),
    )
    op.create_index("ix_auto_exec_tenant_tipo", "auto_execucoes", ["tenant_id", "tipo"])
    op.create_index("ix_auto_exec_tenant_status", "auto_execucoes", ["tenant_id", "status"])

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.drop_table(table)
