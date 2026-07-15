"""Manutenção: OS, preventiva, peças/estoque e pneus.

Revision ID: 0006_manutencao
Revises: 0005_frota
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_manutencao"
down_revision: str | None = "0005_frota"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "man_pecas",
    "man_planos_preventivos",
    "man_plano_checklist",
    "man_veiculo_planos",
    "man_ordens_servico",
    "man_os_itens",
    "man_os_fotos",
    "man_estoque_pecas",
    "man_estoque_movimentos",
    "man_pneus",
    "man_pneu_historico",
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
        "man_pecas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("categoria_codigo", sa.String(60), nullable=True),
        sa.Column("unidade", sa.String(10), nullable=False, server_default="UN"),
        sa.Column("custo_medio", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id", name="pk_man_pecas"),
    )
    op.create_index("ix_man_pecas_tenant_id", "man_pecas", ["tenant_id"])
    op.create_index("ix_man_pecas_tenant_nome", "man_pecas", ["tenant_id", "nome"])
    op.create_index(
        "uq_man_pecas_tenant_codigo_active",
        "man_pecas",
        ["tenant_id", "codigo"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "man_planos_preventivos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("modelo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intervalo_km", sa.Integer(), nullable=True),
        sa.Column("intervalo_meses", sa.Integer(), nullable=True),
        sa.Column("fornecedor_sugerido_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custo_estimado", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("automatico", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_man_planos_preventivos_categoria_id_frota_categorias",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["modelo_id"],
            ["frota_modelos.id"],
            name="fk_man_planos_preventivos_modelo_id_frota_modelos",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["fornecedor_sugerido_id"],
            ["fornecedores.id"],
            name="fk_man_planos_preventivos_fornecedor_sugerido_id_fornecedores",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_planos_preventivos"),
    )
    op.create_index("ix_man_planos_preventivos_tenant_id", "man_planos_preventivos", ["tenant_id"])
    op.create_index(
        "ix_man_planos_preventivos_categoria_id", "man_planos_preventivos", ["categoria_id"]
    )
    op.create_index(
        "ix_man_planos_preventivos_modelo_id", "man_planos_preventivos", ["modelo_id"]
    )
    op.create_index(
        "ix_man_planos_preventivos_fornecedor_sugerido_id",
        "man_planos_preventivos",
        ["fornecedor_sugerido_id"],
    )
    op.create_index(
        "ix_man_planos_preventivos_tenant_nome",
        "man_planos_preventivos",
        ["tenant_id", "nome"],
    )

    op.create_table(
        "man_plano_checklist",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("plano_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_descricao", sa.String(500), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["plano_id"],
            ["man_planos_preventivos.id"],
            name="fk_man_plano_checklist_plano_id_man_planos_preventivos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_plano_checklist"),
    )
    op.create_index("ix_man_plano_checklist_tenant_id", "man_plano_checklist", ["tenant_id"])
    op.create_index("ix_man_plano_checklist_plano_id", "man_plano_checklist", ["plano_id"])
    op.create_index(
        "ix_man_plano_checklist_plano_ordem", "man_plano_checklist", ["plano_id", "ordem"]
    )

    op.create_table(
        "man_veiculo_planos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plano_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("km_ultima_execucao", sa.Integer(), nullable=True),
        sa.Column("data_ultima_execucao", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_man_veiculo_planos_veiculo_id_frota_veiculos",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plano_id"],
            ["man_planos_preventivos.id"],
            name="fk_man_veiculo_planos_plano_id_man_planos_preventivos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_veiculo_planos"),
    )
    op.create_index("ix_man_veiculo_planos_tenant_id", "man_veiculo_planos", ["tenant_id"])
    op.create_index("ix_man_veiculo_planos_veiculo_id", "man_veiculo_planos", ["veiculo_id"])
    op.create_index("ix_man_veiculo_planos_plano_id", "man_veiculo_planos", ["plano_id"])
    op.create_index(
        "uq_man_veiculo_planos_active",
        "man_veiculo_planos",
        ["tenant_id", "veiculo_id", "plano_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "man_ordens_servico",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(25), nullable=False, server_default="aberta"),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("plano_preventivo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("km_entrada", sa.Integer(), nullable=True),
        sa.Column("km_saida", sa.Integer(), nullable=True),
        sa.Column("data_abertura", sa.Date(), nullable=False),
        sa.Column("data_previsao", sa.Date(), nullable=True),
        sa.Column("data_conclusao", sa.Date(), nullable=True),
        sa.Column("custo_mao_obra", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("custo_pecas", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("custo_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column(
            "requer_aprovacao", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprovado_por_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("garantia_dias", sa.Integer(), nullable=True),
        sa.Column("garantia_km", sa.Integer(), nullable=True),
        sa.Column("status_veiculo_anterior", sa.String(20), nullable=True),
        sa.Column("causa", sa.String(15), nullable=True),
        sa.Column("responsavel_custo", sa.String(15), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_man_ordens_servico_veiculo_id_frota_veiculos",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fornecedor_id"],
            ["fornecedores.id"],
            name="fk_man_ordens_servico_fornecedor_id_fornecedores",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"],
            ["filiais.id"],
            name="fk_man_ordens_servico_filial_id_filiais",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["plano_preventivo_id"],
            ["man_planos_preventivos.id"],
            name="fk_man_ordens_servico_plano_preventivo_id_man_planos_preventivos",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["aprovado_por_user_id"],
            ["users.id"],
            name="fk_man_ordens_servico_aprovado_por_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_ordens_servico"),
    )
    op.create_index("ix_man_ordens_servico_tenant_id", "man_ordens_servico", ["tenant_id"])
    op.create_index("ix_man_ordens_servico_veiculo_id", "man_ordens_servico", ["veiculo_id"])
    op.create_index("ix_man_ordens_servico_fornecedor_id", "man_ordens_servico", ["fornecedor_id"])
    op.create_index("ix_man_ordens_servico_filial_id", "man_ordens_servico", ["filial_id"])
    op.create_index(
        "ix_man_ordens_servico_plano_preventivo_id",
        "man_ordens_servico",
        ["plano_preventivo_id"],
    )
    op.create_index(
        "ix_man_ordens_servico_aprovado_por_user_id",
        "man_ordens_servico",
        ["aprovado_por_user_id"],
    )
    op.create_index(
        "ix_man_ordens_servico_tenant_status", "man_ordens_servico", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_man_ordens_servico_tenant_veiculo",
        "man_ordens_servico",
        ["tenant_id", "veiculo_id"],
    )
    op.create_index(
        "ix_man_ordens_servico_tenant_tipo", "man_ordens_servico", ["tenant_id", "tipo"]
    )
    op.create_index(
        "uq_man_ordens_servico_tenant_numero_active",
        "man_ordens_servico",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "man_os_itens",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("os_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_item", sa.String(15), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=False),
        sa.Column("peca_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False, server_default="1"),
        sa.Column("valor_unitario", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["os_id"],
            ["man_ordens_servico.id"],
            name="fk_man_os_itens_os_id_man_ordens_servico",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["peca_id"],
            ["man_pecas.id"],
            name="fk_man_os_itens_peca_id_man_pecas",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_os_itens"),
    )
    op.create_index("ix_man_os_itens_tenant_id", "man_os_itens", ["tenant_id"])
    op.create_index("ix_man_os_itens_os_id", "man_os_itens", ["os_id"])
    op.create_index("ix_man_os_itens_peca_id", "man_os_itens", ["peca_id"])

    op.create_table(
        "man_os_fotos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("os_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("legenda", sa.String(255), nullable=True),
        sa.Column("fase", sa.String(20), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["os_id"],
            ["man_ordens_servico.id"],
            name="fk_man_os_fotos_os_id_man_ordens_servico",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_os_fotos"),
    )
    op.create_index("ix_man_os_fotos_tenant_id", "man_os_fotos", ["tenant_id"])
    op.create_index("ix_man_os_fotos_os_id", "man_os_fotos", ["os_id"])
    op.create_index("ix_man_os_fotos_os_ordem", "man_os_fotos", ["os_id", "ordem"])

    op.create_table(
        "man_estoque_pecas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("peca_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantidade_atual", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("quantidade_minima", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("quantidade_maxima", sa.Numeric(12, 3), nullable=True),
        sa.Column("localizacao", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(
            ["peca_id"],
            ["man_pecas.id"],
            name="fk_man_estoque_pecas_peca_id_man_pecas",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"],
            ["filiais.id"],
            name="fk_man_estoque_pecas_filial_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_estoque_pecas"),
    )
    op.create_index("ix_man_estoque_pecas_tenant_id", "man_estoque_pecas", ["tenant_id"])
    op.create_index("ix_man_estoque_pecas_peca_id", "man_estoque_pecas", ["peca_id"])
    op.create_index("ix_man_estoque_pecas_filial_id", "man_estoque_pecas", ["filial_id"])
    op.create_index(
        "uq_man_estoque_pecas_active",
        "man_estoque_pecas",
        ["tenant_id", "peca_id", "filial_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "man_estoque_movimentos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("peca_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_destino_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
        sa.Column("custo_unitario", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("os_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["peca_id"],
            ["man_pecas.id"],
            name="fk_man_estoque_movimentos_peca_id_man_pecas",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"],
            ["filiais.id"],
            name="fk_man_estoque_movimentos_filial_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["filial_destino_id"],
            ["filiais.id"],
            name="fk_man_estoque_movimentos_filial_destino_id_filiais",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["os_id"],
            ["man_ordens_servico.id"],
            name="fk_man_estoque_movimentos_os_id_man_ordens_servico",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_estoque_movimentos"),
    )
    op.create_index("ix_man_estoque_movimentos_tenant_id", "man_estoque_movimentos", ["tenant_id"])
    op.create_index("ix_man_estoque_movimentos_peca_id", "man_estoque_movimentos", ["peca_id"])
    op.create_index("ix_man_estoque_movimentos_filial_id", "man_estoque_movimentos", ["filial_id"])
    op.create_index(
        "ix_man_estoque_movimentos_filial_destino_id",
        "man_estoque_movimentos",
        ["filial_destino_id"],
    )
    op.create_index("ix_man_estoque_movimentos_os_id", "man_estoque_movimentos", ["os_id"])
    op.create_index(
        "ix_man_estoque_movimentos_peca_ocorrido",
        "man_estoque_movimentos",
        ["peca_id", "ocorrido_em"],
    )

    op.create_table(
        "man_pneus",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero_fogo", sa.String(50), nullable=False),
        sa.Column("marca", sa.String(100), nullable=False),
        sa.Column("modelo", sa.String(100), nullable=True),
        sa.Column("medida", sa.String(30), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posicao", sa.String(10), nullable=True),
        sa.Column("km_instalacao", sa.Integer(), nullable=True),
        sa.Column("km_atual", sa.Integer(), nullable=True),
        sa.Column("vida_util_km", sa.Integer(), nullable=True),
        sa.Column("sulco_mm", sa.Numeric(4, 2), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="novo"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_man_pneus_veiculo_id_frota_veiculos",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_pneus"),
    )
    op.create_index("ix_man_pneus_tenant_id", "man_pneus", ["tenant_id"])
    op.create_index("ix_man_pneus_veiculo_id", "man_pneus", ["veiculo_id"])
    op.create_index("ix_man_pneus_tenant_status", "man_pneus", ["tenant_id", "status"])
    op.create_index(
        "uq_man_pneus_tenant_numero_fogo_active",
        "man_pneus",
        ["tenant_id", "numero_fogo"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "man_pneu_historico",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("pneu_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posicao", sa.String(10), nullable=True),
        sa.Column("km_evento", sa.Integer(), nullable=True),
        sa.Column("tipo_evento", sa.String(20), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["pneu_id"],
            ["man_pneus.id"],
            name="fk_man_pneu_historico_pneu_id_man_pneus",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_man_pneu_historico_veiculo_id_frota_veiculos",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_man_pneu_historico"),
    )
    op.create_index("ix_man_pneu_historico_tenant_id", "man_pneu_historico", ["tenant_id"])
    op.create_index("ix_man_pneu_historico_pneu_id", "man_pneu_historico", ["pneu_id"])
    op.create_index("ix_man_pneu_historico_veiculo_id", "man_pneu_historico", ["veiculo_id"])
    op.create_index(
        "ix_man_pneu_historico_pneu_ocorrido",
        "man_pneu_historico",
        ["pneu_id", "ocorrido_em"],
    )

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("man_pneu_historico")
    op.drop_table("man_pneus")
    op.drop_table("man_estoque_movimentos")
    op.drop_table("man_estoque_pecas")
    op.drop_table("man_os_fotos")
    op.drop_table("man_os_itens")
    op.drop_table("man_ordens_servico")
    op.drop_table("man_veiculo_planos")
    op.drop_table("man_plano_checklist")
    op.drop_table("man_planos_preventivos")
    op.drop_table("man_pecas")
