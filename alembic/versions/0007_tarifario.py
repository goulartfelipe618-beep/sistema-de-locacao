"""Tarifário: tabelas, temporadas, taxas, proteções e políticas de cancelamento.

Revision ID: 0007_tarifario
Revises: 0006_manutencao
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_tarifario"
down_revision: str | None = "0006_manutencao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "tar_tabelas",
    "tar_tabela_itens",
    "tar_temporadas",
    "tar_taxas",
    "tar_protecoes",
    "tar_protecao_categorias",
    "tar_politicas_cancelamento",
    "tar_politica_faixas",
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
        "tar_tabelas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("canal", sa.String(20), nullable=False, server_default="todos"),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parceiro_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prioridade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["filial_id"],
            ["filiais.id"],
            name="fk_tar_tabelas_filial_id_filiais",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parceiro_id"],
            ["parceiros.id"],
            name="fk_tar_tabelas_parceiro_id_parceiros",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name="fk_tar_tabelas_cliente_id_clientes",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tar_tabelas"),
    )
    op.create_index("ix_tar_tabelas_tenant_id", "tar_tabelas", ["tenant_id"])
    op.create_index("ix_tar_tabelas_tenant_nome", "tar_tabelas", ["tenant_id", "nome"])
    op.create_index(
        "ix_tar_tabelas_tenant_vigencia", "tar_tabelas", ["tenant_id", "vigencia_inicio"]
    )
    op.create_index("ix_tar_tabelas_tenant_canal", "tar_tabelas", ["tenant_id", "canal"])
    op.create_index(
        "ix_tar_tabelas_tenant_prioridade", "tar_tabelas", ["tenant_id", "prioridade"]
    )
    op.create_index("ix_tar_tabelas_filial_id", "tar_tabelas", ["filial_id"])
    op.create_index("ix_tar_tabelas_parceiro_id", "tar_tabelas", ["parceiro_id"])
    op.create_index("ix_tar_tabelas_cliente_id", "tar_tabelas", ["cliente_id"])

    op.create_table(
        "tar_tabela_itens",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("tabela_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valor_1_3", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_4_7", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_8_15", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_16_30", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_mensal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("km_livre", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("km_incluido", sa.Integer(), nullable=True),
        sa.Column("valor_km_excedente", sa.Numeric(14, 2), nullable=True),
        sa.ForeignKeyConstraint(
            ["tabela_id"],
            ["tar_tabelas.id"],
            name="fk_tar_tabela_itens_tabela_id_tar_tabelas",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_tar_tabela_itens_categoria_id_frota_categorias",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tar_tabela_itens"),
    )
    op.create_index("ix_tar_tabela_itens_tenant_id", "tar_tabela_itens", ["tenant_id"])
    op.create_index("ix_tar_tabela_itens_tabela_id", "tar_tabela_itens", ["tabela_id"])
    op.create_index("ix_tar_tabela_itens_categoria_id", "tar_tabela_itens", ["categoria_id"])
    op.create_index(
        "uq_tar_tabela_itens_tabela_categoria_active",
        "tar_tabela_itens",
        ["tenant_id", "tabela_id", "categoria_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "tar_temporadas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("tipo_ajuste", sa.String(30), nullable=False),
        sa.Column("valor_ajuste", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tabela_alternativa_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("estadia_minima", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prioridade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(
            ["tabela_alternativa_id"],
            ["tar_tabelas.id"],
            name="fk_tar_temporadas_tabela_alternativa_id_tar_tabelas",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"],
            ["filiais.id"],
            name="fk_tar_temporadas_filial_id_filiais",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_tar_temporadas_categoria_id_frota_categorias",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tar_temporadas"),
    )
    op.create_index("ix_tar_temporadas_tenant_id", "tar_temporadas", ["tenant_id"])
    op.create_index(
        "ix_tar_temporadas_tenant_periodo",
        "tar_temporadas",
        ["tenant_id", "data_inicio", "data_fim"],
    )
    op.create_index(
        "ix_tar_temporadas_tenant_prioridade", "tar_temporadas", ["tenant_id", "prioridade"]
    )
    op.create_index(
        "ix_tar_temporadas_tabela_alternativa_id", "tar_temporadas", ["tabela_alternativa_id"]
    )
    op.create_index("ix_tar_temporadas_filial_id", "tar_temporadas", ["filial_id"])
    op.create_index("ix_tar_temporadas_categoria_id", "tar_temporadas", ["categoria_id"])

    op.create_table(
        "tar_taxas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo_calculo", sa.String(20), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("aplicacao", sa.String(20), nullable=False, server_default="opcional"),
        sa.Column("regra_codigo", sa.String(40), nullable=True),
        sa.Column("tributavel", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id", name="pk_tar_taxas"),
    )
    op.create_index("ix_tar_taxas_tenant_id", "tar_taxas", ["tenant_id"])
    op.create_index("ix_tar_taxas_tenant_nome", "tar_taxas", ["tenant_id", "nome"])

    op.create_table(
        "tar_protecoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("valor_diaria", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("franquia", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exclusoes", sa.Text(), nullable=True),
        sa.Column("obrigatoria", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(
            ["fornecedor_id"],
            ["fornecedores.id"],
            name="fk_tar_protecoes_fornecedor_id_fornecedores",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tar_protecoes"),
    )
    op.create_index("ix_tar_protecoes_tenant_id", "tar_protecoes", ["tenant_id"])
    op.create_index("ix_tar_protecoes_tenant_nome", "tar_protecoes", ["tenant_id", "nome"])
    op.create_index("ix_tar_protecoes_fornecedor_id", "tar_protecoes", ["fornecedor_id"])

    op.create_table(
        "tar_protecao_categorias",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("protecao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["protecao_id"],
            ["tar_protecoes.id"],
            name="fk_tar_protecao_categorias_protecao_id_tar_protecoes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_tar_protecao_categorias_categoria_id_frota_categorias",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tar_protecao_categorias"),
    )
    op.create_index(
        "ix_tar_protecao_categorias_tenant_id", "tar_protecao_categorias", ["tenant_id"]
    )
    op.create_index(
        "ix_tar_protecao_categorias_protecao_id", "tar_protecao_categorias", ["protecao_id"]
    )
    op.create_index(
        "ix_tar_protecao_categorias_categoria_id", "tar_protecao_categorias", ["categoria_id"]
    )
    op.create_index(
        "uq_tar_protecao_categorias_active",
        "tar_protecao_categorias",
        ["tenant_id", "protecao_id", "categoria_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "tar_politicas_cancelamento",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("canal", sa.String(20), nullable=False, server_default="todos"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_tar_politicas_cancelamento"),
    )
    op.create_index(
        "ix_tar_politicas_cancelamento_tenant_id", "tar_politicas_cancelamento", ["tenant_id"]
    )
    op.create_index(
        "ix_tar_politicas_cancelamento_tenant_nome",
        "tar_politicas_cancelamento",
        ["tenant_id", "nome"],
    )

    op.create_table(
        "tar_politica_faixas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("politica_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horas_antes_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("horas_antes_max", sa.Integer(), nullable=True),
        sa.Column("tipo_retencao", sa.String(20), nullable=False),
        sa.Column("valor_retencao", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["politica_id"],
            ["tar_politicas_cancelamento.id"],
            name="fk_tar_politica_faixas_politica_id_tar_politicas_cancelamento",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tar_politica_faixas"),
    )
    op.create_index("ix_tar_politica_faixas_tenant_id", "tar_politica_faixas", ["tenant_id"])
    op.create_index("ix_tar_politica_faixas_politica_id", "tar_politica_faixas", ["politica_id"])
    op.create_index(
        "ix_tar_politica_faixas_politica_ordem", "tar_politica_faixas", ["politica_id", "ordem"]
    )

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("tar_politica_faixas")
    op.drop_table("tar_politicas_cancelamento")
    op.drop_table("tar_protecao_categorias")
    op.drop_table("tar_protecoes")
    op.drop_table("tar_taxas")
    op.drop_table("tar_temporadas")
    op.drop_table("tar_tabela_itens")
    op.drop_table("tar_tabelas")
