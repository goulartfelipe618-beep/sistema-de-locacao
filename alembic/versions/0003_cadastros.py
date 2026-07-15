"""Cadastros: tabelas auxiliares e clientes (com RLS).

Revision ID: 0003_cadastros
Revises: 0002_foundation_hardening
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_cadastros"
down_revision: str | None = "0002_foundation_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_SCOPED = ("tabelas_auxiliares", "clientes")


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
        "tabelas_auxiliares",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grupo", sa.String(60), nullable=False),
        sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sistema", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id", name="pk_tabelas_auxiliares"),
        sa.UniqueConstraint(
            "tenant_id",
            "grupo",
            "codigo",
            name="uq_tabelas_auxiliares_tenant_grupo_codigo",
        ),
    )
    op.create_index("ix_tabelas_auxiliares_tenant_id", "tabelas_auxiliares", ["tenant_id"])
    op.create_index("ix_tabelas_auxiliares_grupo", "tabelas_auxiliares", ["grupo"])
    op.create_index(
        "ix_tabelas_auxiliares_tenant_grupo",
        "tabelas_auxiliares",
        ["tenant_id", "grupo"],
    )

    op.create_table(
        "clientes",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("person_type", sa.String(5), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_fantasia", sa.String(200), nullable=True),
        sa.Column("cpf", sa.String(11), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("rg", sa.String(20), nullable=True),
        sa.Column("ie", sa.String(30), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("estado_civil", sa.String(40), nullable=True),
        sa.Column("profissao", sa.String(100), nullable=True),
        sa.Column("representante_legal", sa.String(200), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("celular", sa.String(20), nullable=True),
        sa.Column("whatsapp", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cep", sa.String(8), nullable=True),
        sa.Column("endereco", sa.String(255), nullable=True),
        sa.Column("numero", sa.String(20), nullable=True),
        sa.Column("complemento", sa.String(100), nullable=True),
        sa.Column("bairro", sa.String(100), nullable=True),
        sa.Column("cidade", sa.String(100), nullable=True),
        sa.Column("uf", sa.String(2), nullable=True),
        sa.Column("categoria_codigo", sa.String(60), nullable=True),
        sa.Column(
            "limite_credito",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("blacklist", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("motivo_bloqueio", sa.String(255), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["filial_id"],
            ["filiais.id"],
            name="fk_clientes_filial_id_filiais",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_clientes"),
    )
    op.create_index("ix_clientes_tenant_id", "clientes", ["tenant_id"])
    op.create_index("ix_clientes_filial_id", "clientes", ["filial_id"])
    op.create_index("ix_clientes_tenant_nome", "clientes", ["tenant_id", "nome"])
    op.create_index(
        "uq_clientes_tenant_cpf_active",
        "clientes",
        ["tenant_id", "cpf"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cpf IS NOT NULL"),
    )
    op.create_index(
        "uq_clientes_tenant_cnpj_active",
        "clientes",
        ["tenant_id", "cnpj"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cnpj IS NOT NULL"),
    )

    for table in _TENANT_SCOPED:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TENANT_SCOPED):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("clientes")
    op.drop_table("tabelas_auxiliares")
