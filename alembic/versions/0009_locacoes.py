"""Locações: contratos, vistorias, avarias e multas.

Revision ID: 0009_locacoes
Revises: 0008_reservas
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_locacoes"
down_revision: str | None = "0008_reservas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "loc_contratos",
    "loc_contrato_motoristas",
    "loc_contrato_itens",
    "loc_contrato_aditivos",
    "loc_vistorias",
    "loc_vistoria_fotos",
    "loc_avarias",
    "loc_avaria_fotos",
    "loc_multas",
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
        sa.Column("caucao", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
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
        "loc_contratos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(25), nullable=False, server_default="rascunho"),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_retirada_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_devolucao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retirada_prevista_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("devolucao_prevista_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checkout_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkin_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("km_saida", sa.Integer(), nullable=True),
        sa.Column("km_entrada", sa.Integer(), nullable=True),
        sa.Column("combustivel_saida", sa.Integer(), nullable=True),
        sa.Column("combustivel_entrada", sa.Integer(), nullable=True),
        *_pricing_columns(),
        sa.Column("ajustes_checkin", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_final", sa.Numeric(14, 2), nullable=True),
        sa.Column("forma_pagamento", sa.String(60), nullable=True),
        sa.Column("condicao", sa.String(25), nullable=False, server_default="avista"),
        sa.Column("pricing_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("politica_snapshot", sa.Text(), nullable=True),
        sa.Column("clausulas_combustivel", sa.Text(), nullable=True),
        sa.Column("assinatura_tipo", sa.String(20), nullable=True),
        sa.Column("assinatura_key", sa.String(500), nullable=True),
        sa.Column("pendencia_financeira", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "combustivel_saida IS NULL OR (combustivel_saida >= 0 AND combustivel_saida <= 8)",
            name="ck_loc_contratos_combustivel_saida",
        ),
        sa.CheckConstraint(
            "combustivel_entrada IS NULL OR (combustivel_entrada >= 0 AND combustivel_entrada <= 8)",
            name="ck_loc_contratos_combustivel_entrada",
        ),
        sa.ForeignKeyConstraint(
            ["reserva_id"],
            ["res_reservas.id"],
            name="fk_loc_contratos_reserva_id_res_reservas",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name="fk_loc_contratos_cliente_id_clientes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_loc_contratos_veiculo_id_frota_veiculos",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_loc_contratos_categoria_id_frota_categorias",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["filial_retirada_id"],
            ["filiais.id"],
            name="fk_loc_contratos_filial_retirada_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["filial_devolucao_id"],
            ["filiais.id"],
            name="fk_loc_contratos_filial_devolucao_id_filiais",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_contratos"),
    )
    op.create_index("ix_loc_contratos_tenant_id", "loc_contratos", ["tenant_id"])
    op.create_index("ix_loc_contratos_tenant_status", "loc_contratos", ["tenant_id", "status"])
    op.create_index("ix_loc_contratos_veiculo_id", "loc_contratos", ["veiculo_id"])
    op.create_index("ix_loc_contratos_cliente_id", "loc_contratos", ["cliente_id"])
    op.create_index("ix_loc_contratos_reserva_id", "loc_contratos", ["reserva_id"])
    op.create_index(
        "uq_loc_contratos_tenant_numero_active",
        "loc_contratos",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "loc_contrato_motoristas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motorista_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["loc_contratos.id"],
            name="fk_loc_contrato_motoristas_contrato_id_loc_contratos",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["motorista_id"],
            ["motoristas.id"],
            name="fk_loc_contrato_motoristas_motorista_id_motoristas",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_contrato_motoristas"),
    )
    op.create_index("ix_loc_contrato_motoristas_tenant_id", "loc_contrato_motoristas", ["tenant_id"])
    op.create_index(
        "ix_loc_contrato_motoristas_contrato_id", "loc_contrato_motoristas", ["contrato_id"]
    )
    op.create_index(
        "ix_loc_contrato_motoristas_motorista_id", "loc_contrato_motoristas", ["motorista_id"]
    )
    op.create_index(
        "uq_loc_contrato_motoristas_active",
        "loc_contrato_motoristas",
        ["tenant_id", "contrato_id", "motorista_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "loc_contrato_itens",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("referencia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("quantidade", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("valor_unitario", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["loc_contratos.id"],
            name="fk_loc_contrato_itens_contrato_id_loc_contratos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_contrato_itens"),
    )
    op.create_index("ix_loc_contrato_itens_tenant_id", "loc_contrato_itens", ["tenant_id"])
    op.create_index("ix_loc_contrato_itens_contrato_id", "loc_contrato_itens", ["contrato_id"])

    op.create_table(
        "loc_contrato_aditivos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("devolucao_anterior", sa.DateTime(timezone=True), nullable=False),
        sa.Column("devolucao_nova", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dias_extra", sa.Integer(), nullable=False),
        sa.Column("valor_aditivo", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("pricing_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("aprovado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("motivo", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["loc_contratos.id"],
            name="fk_loc_contrato_aditivos_contrato_id_loc_contratos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_contrato_aditivos"),
    )
    op.create_index("ix_loc_contrato_aditivos_tenant_id", "loc_contrato_aditivos", ["tenant_id"])
    op.create_index(
        "ix_loc_contrato_aditivos_contrato_id", "loc_contrato_aditivos", ["contrato_id"]
    )
    op.create_index(
        "ix_loc_contrato_aditivos_tenant_contrato",
        "loc_contrato_aditivos",
        ["tenant_id", "contrato_id"],
    )

    op.create_table(
        "loc_vistorias",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("km", sa.Integer(), nullable=False),
        sa.Column("combustivel_nivel", sa.Integer(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("realizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realizado_por_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checklist_json", sa.Text(), nullable=False, server_default="{}"),
        sa.CheckConstraint(
            "combustivel_nivel >= 0 AND combustivel_nivel <= 8",
            name="ck_loc_vistorias_combustivel_nivel",
        ),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["loc_contratos.id"],
            name="fk_loc_vistorias_contrato_id_loc_contratos",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["realizado_por_user_id"],
            ["users.id"],
            name="fk_loc_vistorias_realizado_por_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_vistorias"),
    )
    op.create_index("ix_loc_vistorias_tenant_id", "loc_vistorias", ["tenant_id"])
    op.create_index("ix_loc_vistorias_contrato_id", "loc_vistorias", ["contrato_id"])
    op.create_index("ix_loc_vistorias_tenant_tipo", "loc_vistorias", ["tenant_id", "tipo"])

    op.create_table(
        "loc_vistoria_fotos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("vistoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("angulo", sa.String(30), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["vistoria_id"],
            ["loc_vistorias.id"],
            name="fk_loc_vistoria_fotos_vistoria_id_loc_vistorias",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_vistoria_fotos"),
    )
    op.create_index("ix_loc_vistoria_fotos_tenant_id", "loc_vistoria_fotos", ["tenant_id"])
    op.create_index("ix_loc_vistoria_fotos_vistoria_id", "loc_vistoria_fotos", ["vistoria_id"])

    op.create_table(
        "loc_avarias",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vistoria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("origem", sa.String(15), nullable=False),
        sa.Column("localizacao", sa.String(100), nullable=False),
        sa.Column("severidade", sa.String(10), nullable=False),
        sa.Column("responsabilidade", sa.String(15), nullable=True),
        sa.Column("laudo", sa.Text(), nullable=True),
        sa.Column("valor_reparo", sa.Numeric(14, 2), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="registrada"),
        sa.Column("os_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_loc_avarias_veiculo_id_frota_veiculos",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["loc_contratos.id"],
            name="fk_loc_avarias_contrato_id_loc_contratos",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["vistoria_id"],
            ["loc_vistorias.id"],
            name="fk_loc_avarias_vistoria_id_loc_vistorias",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["os_id"],
            ["man_ordens_servico.id"],
            name="fk_loc_avarias_os_id_man_ordens_servico",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_avarias"),
    )
    op.create_index("ix_loc_avarias_tenant_id", "loc_avarias", ["tenant_id"])
    op.create_index("ix_loc_avarias_veiculo_id", "loc_avarias", ["veiculo_id"])
    op.create_index("ix_loc_avarias_contrato_id", "loc_avarias", ["contrato_id"])
    op.create_index("ix_loc_avarias_tenant_status", "loc_avarias", ["tenant_id", "status"])

    op.create_table(
        "loc_avaria_fotos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("avaria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("legenda", sa.String(200), nullable=True),
        sa.ForeignKeyConstraint(
            ["avaria_id"],
            ["loc_avarias.id"],
            name="fk_loc_avaria_fotos_avaria_id_loc_avarias",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_avaria_fotos"),
    )
    op.create_index("ix_loc_avaria_fotos_tenant_id", "loc_avaria_fotos", ["tenant_id"])
    op.create_index("ix_loc_avaria_fotos_avaria_id", "loc_avaria_fotos", ["avaria_id"])

    op.create_table(
        "loc_multas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("motorista_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("orgao", sa.String(120), nullable=False),
        sa.Column("codigo_infracao", sa.String(20), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("pontuacao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ait", sa.String(40), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="recebida"),
        sa.Column("taxa_admin", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_loc_multas_veiculo_id_frota_veiculos",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["loc_contratos.id"],
            name="fk_loc_multas_contrato_id_loc_contratos",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name="fk_loc_multas_cliente_id_clientes",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["motorista_id"],
            ["motoristas.id"],
            name="fk_loc_multas_motorista_id_motoristas",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loc_multas"),
    )
    op.create_index("ix_loc_multas_tenant_id", "loc_multas", ["tenant_id"])
    op.create_index("ix_loc_multas_veiculo_id", "loc_multas", ["veiculo_id"])
    op.create_index("ix_loc_multas_contrato_id", "loc_multas", ["contrato_id"])
    op.create_index("ix_loc_multas_tenant_status", "loc_multas", ["tenant_id", "status"])
    op.create_index("ix_loc_multas_ocorrido_em", "loc_multas", ["ocorrido_em"])

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("loc_multas")
    op.drop_table("loc_avaria_fotos")
    op.drop_table("loc_avarias")
    op.drop_table("loc_vistoria_fotos")
    op.drop_table("loc_vistorias")
    op.drop_table("loc_contrato_aditivos")
    op.drop_table("loc_contrato_itens")
    op.drop_table("loc_contrato_motoristas")
    op.drop_table("loc_contratos")
