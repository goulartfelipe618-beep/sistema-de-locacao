"""Motor de PDF: documentos_gerados (§16).

Revision ID: 0017_documentos
Revises: 0016_parametros
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_documentos"
down_revision: str | None = "0016_parametros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        "documentos_gerados",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_id", sa.String(60), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("familia", sa.String(15), nullable=False),
        sa.Column("entidade_tipo", sa.String(40), nullable=True),
        sa.Column("entidade_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="pendente"),
        sa.Column("sincrono", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("watermark", sa.String(40), nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("conteudo_inline", sa.LargeBinary(), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=False, server_default="application/pdf"),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=True),
        sa.Column("hash_sha256", sa.String(64), nullable=True),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["filial_id"], ["filiais.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_documentos_gerados_tenant_status", "documentos_gerados", ["tenant_id", "status"])
    op.create_index(
        "ix_documentos_gerados_tenant_template", "documentos_gerados", ["tenant_id", "template_id"]
    )
    op.create_index(
        "ix_documentos_gerados_entidade", "documentos_gerados", ["entidade_tipo", "entidade_id"]
    )
    op.create_index("ix_documentos_gerados_user_id", "documentos_gerados", ["user_id"])
    _enable_rls("documentos_gerados")


def downgrade() -> None:
    op.drop_table("documentos_gerados")
