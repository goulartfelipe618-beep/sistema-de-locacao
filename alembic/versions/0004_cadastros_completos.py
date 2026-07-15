"""Cadastros restantes: motoristas, parceiros, fornecedores, vendedores.

Revision ID: 0004_cadastros_completos
Revises: 0003_cadastros
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_cadastros_completos"
down_revision: str | None = "0003_cadastros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("motoristas", "parceiros", "fornecedores", "vendedores")


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
        "motoristas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vinculo", sa.String(20), nullable=False, server_default="terceiro"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("cpf", sa.String(11), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("celular", sa.String(20), nullable=True),
        sa.Column("cnh_numero", sa.String(20), nullable=True),
        sa.Column("cnh_categoria", sa.String(10), nullable=True),
        sa.Column("cnh_emissao", sa.Date(), nullable=True),
        sa.Column("cnh_validade", sa.Date(), nullable=True),
        sa.Column("cnh_orgao", sa.String(60), nullable=True),
        sa.Column("cnh_status", sa.String(20), nullable=False, server_default="regular"),
        sa.Column("cnh_pontuacao", sa.Integer(), nullable=True),
        sa.Column("cnh_frente_key", sa.String(500), nullable=True),
        sa.Column("cnh_verso_key", sa.String(500), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"], name="fk_motoristas_cliente_id_clientes",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_motoristas"),
    )
    op.create_index("ix_motoristas_tenant_id", "motoristas", ["tenant_id"])
    op.create_index("ix_motoristas_cliente_id", "motoristas", ["cliente_id"])
    op.create_index("ix_motoristas_tenant_nome", "motoristas", ["tenant_id", "nome"])
    op.create_index(
        "uq_motoristas_tenant_cpf_active",
        "motoristas",
        ["tenant_id", "cpf"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cpf IS NOT NULL"),
    )
    op.create_index(
        "uq_motoristas_tenant_cnh_active",
        "motoristas",
        ["tenant_id", "cnh_numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cnh_numero IS NOT NULL"),
    )

    op.create_table(
        "parceiros",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("person_type", sa.String(5), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="indicacao"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_fantasia", sa.String(200), nullable=True),
        sa.Column("cpf", sa.String(11), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("comissao_percentual", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("comissao_valor_fixo", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("banco", sa.String(100), nullable=True),
        sa.Column("agencia", sa.String(20), nullable=True),
        sa.Column("conta", sa.String(30), nullable=True),
        sa.Column("pix_chave", sa.String(140), nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=True),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_parceiros"),
    )
    op.create_index("ix_parceiros_tenant_id", "parceiros", ["tenant_id"])
    op.create_index("ix_parceiros_tenant_nome", "parceiros", ["tenant_id", "nome"])
    op.create_index(
        "uq_parceiros_tenant_cpf_active",
        "parceiros",
        ["tenant_id", "cpf"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cpf IS NOT NULL"),
    )
    op.create_index(
        "uq_parceiros_tenant_cnpj_active",
        "parceiros",
        ["tenant_id", "cnpj"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cnpj IS NOT NULL"),
    )

    op.create_table(
        "fornecedores",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_fantasia", sa.String(200), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("ie", sa.String(30), nullable=True),
        sa.Column("categoria_codigo", sa.String(60), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("celular", sa.String(20), nullable=True),
        sa.Column("cep", sa.String(8), nullable=True),
        sa.Column("endereco", sa.String(255), nullable=True),
        sa.Column("numero", sa.String(20), nullable=True),
        sa.Column("complemento", sa.String(100), nullable=True),
        sa.Column("bairro", sa.String(100), nullable=True),
        sa.Column("cidade", sa.String(100), nullable=True),
        sa.Column("uf", sa.String(2), nullable=True),
        sa.Column("banco", sa.String(100), nullable=True),
        sa.Column("agencia", sa.String(20), nullable=True),
        sa.Column("conta", sa.String(30), nullable=True),
        sa.Column("pix_chave", sa.String(140), nullable=True),
        sa.Column("prazo_pagamento_dias", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("desconto_percentual", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("bloqueado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("motivo_bloqueio", sa.String(255), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_fornecedores"),
    )
    op.create_index("ix_fornecedores_tenant_id", "fornecedores", ["tenant_id"])
    op.create_index("ix_fornecedores_tenant_nome", "fornecedores", ["tenant_id", "nome"])
    op.create_index(
        "uq_fornecedores_tenant_cnpj_active",
        "fornecedores",
        ["tenant_id", "cnpj"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND cnpj IS NOT NULL"),
    )

    op.create_table(
        "vendedores",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("meta_contratos_mes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta_faturamento_mes", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("comissao_percentual", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["users.id"], name="fk_vendedores_usuario_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"], name="fk_vendedores_filial_id_filiais",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vendedores"),
    )
    op.create_index("ix_vendedores_tenant_id", "vendedores", ["tenant_id"])
    op.create_index("ix_vendedores_usuario_id", "vendedores", ["usuario_id"])
    op.create_index("ix_vendedores_filial_id", "vendedores", ["filial_id"])
    op.create_index("ix_vendedores_tenant_nome", "vendedores", ["tenant_id", "nome"])
    op.create_index(
        "uq_vendedores_tenant_usuario_active",
        "vendedores",
        ["tenant_id", "usuario_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND usuario_id IS NOT NULL"),
    )

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("vendedores")
    op.drop_table("fornecedores")
    op.drop_table("parceiros")
    op.drop_table("motoristas")
