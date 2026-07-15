"""Reservas: reservas, cotações, disponibilidade e calendário.

Revision ID: 0008_reservas
Revises: 0007_tarifario
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_reservas"
down_revision: str | None = "0007_tarifario"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "res_reservas",
    "res_cotacoes",
    "res_reserva_motoristas",
    "res_reserva_itens",
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


def _pricing_columns() -> list[sa.Column]:
    return [
        sa.Column("diaria_unitaria", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("dias", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_taxas", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_protecoes", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_acessorios", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("desconto", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("pricing_snapshot", sa.Text(), nullable=False, server_default="{}"),
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
        "res_reservas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("alocacao", sa.String(20), nullable=False, server_default="categoria"),
        sa.Column("origem", sa.String(20), nullable=False, server_default="balcao"),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_retirada_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_devolucao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retirada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("devolucao_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("endereco_entrega", sa.Text(), nullable=True),
        sa.Column("vendedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parceiro_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("politica_cancelamento_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("forma_pagamento_prevista", sa.String(60), nullable=True),
        sa.Column("cupom_codigo", sa.String(40), nullable=True),
        *_pricing_columns(),
        sa.Column("politica_snapshot", sa.Text(), nullable=True),
        sa.Column("motivo_cancelamento", sa.String(255), nullable=True),
        sa.Column("valor_retencao", sa.Numeric(14, 2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("requer_aprovacao", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name="fk_res_reservas_cliente_id_clientes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_res_reservas_categoria_id_frota_categorias",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_res_reservas_veiculo_id_frota_veiculos",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_retirada_id"],
            ["filiais.id"],
            name="fk_res_reservas_filial_retirada_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["filial_devolucao_id"],
            ["filiais.id"],
            name="fk_res_reservas_filial_devolucao_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vendedor_id"],
            ["vendedores.id"],
            name="fk_res_reservas_vendedor_id_vendedores",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parceiro_id"],
            ["parceiros.id"],
            name="fk_res_reservas_parceiro_id_parceiros",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["politica_cancelamento_id"],
            ["tar_politicas_cancelamento.id"],
            name="fk_res_res_pol_cancel_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_res_reservas"),
    )
    op.create_index("ix_res_reservas_tenant_id", "res_reservas", ["tenant_id"])
    op.create_index("ix_res_reservas_tenant_status", "res_reservas", ["tenant_id", "status"])
    op.create_index(
        "ix_res_reservas_tenant_retirada", "res_reservas", ["tenant_id", "retirada_em"]
    )
    op.create_index("ix_res_reservas_veiculo_id", "res_reservas", ["veiculo_id"])
    op.create_index(
        "uq_res_reservas_tenant_numero_active",
        "res_reservas",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "res_cotacoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberta"),
        sa.Column("validade_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filial_retirada_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_devolucao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retirada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("devolucao_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_reserva_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("origem", sa.String(20), nullable=False, server_default="balcao"),
        sa.Column("parceiro_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_pricing_columns(),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["filial_retirada_id"],
            ["filiais.id"],
            name="fk_res_cotacoes_filial_retirada_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["filial_devolucao_id"],
            ["filiais.id"],
            name="fk_res_cotacoes_filial_devolucao_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_res_cotacoes_categoria_id_frota_categorias",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_res_cotacoes_veiculo_id_frota_veiculos",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name="fk_res_cotacoes_cliente_id_clientes",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["converted_reserva_id"],
            ["res_reservas.id"],
            name="fk_res_cotacoes_converted_reserva_id_res_reservas",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parceiro_id"],
            ["parceiros.id"],
            name="fk_res_cotacoes_parceiro_id_parceiros",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_res_cotacoes"),
    )
    op.create_index("ix_res_cotacoes_tenant_id", "res_cotacoes", ["tenant_id"])
    op.create_index("ix_res_cotacoes_tenant_status", "res_cotacoes", ["tenant_id", "status"])
    op.create_index("ix_res_cotacoes_validade", "res_cotacoes", ["validade_em"])
    op.create_index(
        "uq_res_cotacoes_tenant_numero_active",
        "res_cotacoes",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "res_reserva_motoristas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motorista_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["reserva_id"],
            ["res_reservas.id"],
            name="fk_res_reserva_motoristas_reserva_id_res_reservas",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["motorista_id"],
            ["motoristas.id"],
            name="fk_res_reserva_motoristas_motorista_id_motoristas",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_res_reserva_motoristas"),
    )
    op.create_index("ix_res_reserva_motoristas_tenant_id", "res_reserva_motoristas", ["tenant_id"])
    op.create_index("ix_res_reserva_motoristas_reserva_id", "res_reserva_motoristas", ["reserva_id"])
    op.create_index(
        "ix_res_reserva_motoristas_motorista_id", "res_reserva_motoristas", ["motorista_id"]
    )
    op.create_index(
        "uq_res_reserva_motoristas_active",
        "res_reserva_motoristas",
        ["tenant_id", "reserva_id", "motorista_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "res_reserva_itens",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("referencia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("quantidade", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("valor_unitario", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["reserva_id"],
            ["res_reservas.id"],
            name="fk_res_reserva_itens_reserva_id_res_reservas",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_res_reserva_itens"),
    )
    op.create_index("ix_res_reserva_itens_tenant_id", "res_reserva_itens", ["tenant_id"])
    op.create_index("ix_res_reserva_itens_reserva_id", "res_reserva_itens", ["reserva_id"])

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("res_reserva_itens")
    op.drop_table("res_reserva_motoristas")
    op.drop_table("res_cotacoes")
    op.drop_table("res_reservas")
