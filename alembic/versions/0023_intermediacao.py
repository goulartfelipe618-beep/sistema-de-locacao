"""Intermediação: locação terceirizada, contratos com parceiros e repasse.

Revision ID: 0023_intermediacao
Revises: 0022_remove_whatsapp_redes
Create Date: 2026-07-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_intermediacao"
down_revision: str | None = "0022_remove_whatsapp_redes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_TABLES = (
    "intermediacao_configs",
    "fornecedor_contratos_locacao",
    "fornecedor_contratos_precos",
    "frota_indisponibilidade_terceiro",
    "loc_repasse_lancamentos",
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
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
        "intermediacao_configs",
        _uuid_pk(),
        _tenant(),
        sa.Column("modo_operacao", sa.String(20), nullable=False, server_default="hibrida"),
        sa.Column("exige_contrato_fornecedor", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("aprovar_reserva_automaticamente", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("publicar_terceiros_site", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("margem_minima_percentual", sa.Numeric(7, 4), nullable=False, server_default="10"),
        sa.Column("buffer_disponibilidade_horas", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("priorizar_frota_propria", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("observacoes", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("uq_intermediacao_configs_tenant_active", "intermediacao_configs", ["tenant_id"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "fornecedor_contratos_locacao",
        _uuid_pk(),
        _tenant(),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fornecedores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("modelo_negocio", sa.String(20), nullable=False, server_default="repasse"),
        sa.Column("tipo_calculo", sa.String(25), nullable=False, server_default="percentual_receita"),
        sa.Column("percentual_repasse", sa.Numeric(7, 4), nullable=True),
        sa.Column("percentual_comissao", sa.Numeric(7, 4), nullable=True),
        sa.Column("valor_diaria_repasse", sa.Numeric(14, 2), nullable=True),
        sa.Column("margem_minima_percentual", sa.Numeric(7, 4), nullable=True),
        sa.Column("prazo_pagamento_dias", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("km_livre_dia", sa.Integer(), nullable=True),
        sa.Column("valor_km_excedente", sa.Numeric(14, 2), nullable=True),
        sa.Column("seguro_incluso", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("documento_storage_key", sa.String(500), nullable=True),
        sa.Column("clausulas", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_fornecedor_contratos_locacao_fornecedor", "fornecedor_contratos_locacao", ["fornecedor_id"])
    op.create_index("uq_fornecedor_contratos_locacao_numero_active", "fornecedor_contratos_locacao", ["tenant_id", "numero"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "fornecedor_contratos_precos",
        _uuid_pk(),
        _tenant(),
        sa.Column("contrato_fornecedor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fornecedor_contratos_locacao.id", ondelete="CASCADE"), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("frota_categorias.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("filiais.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fim", sa.Time(), nullable=True),
        sa.Column("dias_minimos", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("dias_maximos", sa.Integer(), nullable=True),
        sa.Column("valor_cliente_diaria", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_repasse_diaria", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_hora_extra_cliente", sa.Numeric(14, 2), nullable=True),
        sa.Column("valor_hora_extra_repasse", sa.Numeric(14, 2), nullable=True),
        sa.Column("percentual_comissao", sa.Numeric(7, 4), nullable=True),
        sa.Column("taxa_entrega", sa.Numeric(14, 2), nullable=True),
        sa.Column("prioridade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        *_timestamps(),
    )

    op.add_column("fornecedores", sa.Column("locadora_parceira", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("fornecedores", sa.Column("modelo_negocio_padrao", sa.String(20), nullable=True))
    op.add_column("fornecedores", sa.Column("contato_operacional_nome", sa.String(200), nullable=True))
    op.add_column("fornecedores", sa.Column("contato_operacional_telefone", sa.String(20), nullable=True))
    op.add_column("fornecedores", sa.Column("contato_operacional_email", sa.String(255), nullable=True))
    op.add_column("fornecedores", sa.Column("margem_padrao_percentual", sa.Numeric(7, 4), nullable=True))

    op.add_column("frota_veiculos", sa.Column("contrato_fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("frota_veiculos", sa.Column("publicar_site", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("frota_veiculos", sa.Column("exige_aprovacao_fornecedor", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.create_foreign_key("fk_frota_veiculos_contrato_fornecedor", "frota_veiculos", "fornecedor_contratos_locacao", ["contrato_fornecedor_id"], ["id"], ondelete="SET NULL")

    for table in ("res_reservas", "loc_contratos"):
        op.add_column(table, sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(table, sa.Column("contrato_fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(table, sa.Column("modelo_negocio_terceiro", sa.String(20), nullable=True))
        op.add_column(table, sa.Column("intermediacao_status", sa.String(25), nullable=False, server_default="nao_aplicavel"))
        op.add_column(table, sa.Column("valor_repasse_total", sa.Numeric(14, 2), nullable=True))
        op.add_column(table, sa.Column("valor_margem", sa.Numeric(14, 2), nullable=True))
        op.add_column(table, sa.Column("valor_comissao", sa.Numeric(14, 2), nullable=True))
        op.add_column(table, sa.Column("repasse_snapshot", sa.Text(), nullable=True))
        op.create_foreign_key(f"fk_{table}_fornecedor", table, "fornecedores", ["fornecedor_id"], ["id"], ondelete="SET NULL")
        op.create_foreign_key(f"fk_{table}_contrato_fornecedor", table, "fornecedor_contratos_locacao", ["contrato_fornecedor_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "frota_indisponibilidade_terceiro",
        _uuid_pk(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("frota_veiculos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fornecedores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo", sa.String(30), nullable=False, server_default="locado_pelo_proprietario"),
        sa.Column("sincronizar_site", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("registrado_por_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "loc_repasse_lancamentos",
        _uuid_pk(),
        _tenant(),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loc_contratos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("res_reservas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fornecedores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contrato_fornecedor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fornecedor_contratos_locacao.id", ondelete="SET NULL"), nullable=True),
        sa.Column("modelo_negocio", sa.String(20), nullable=False),
        sa.Column("valor_cliente", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_repasse", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_margem", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_comissao", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("conta_pagar_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fin_contas_pagar.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conta_receber_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fin_contas_receber.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vencimento", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="em_aberto"),
        sa.Column("repasse_snapshot", sa.Text(), nullable=False, server_default="{}"),
        *_timestamps(),
    )

    for table in _NEW_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    op.drop_table("loc_repasse_lancamentos")
    op.drop_table("frota_indisponibilidade_terceiro")
    for table in ("loc_contratos", "res_reservas"):
        op.drop_constraint(f"fk_{table}_contrato_fornecedor", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_fornecedor", table, type_="foreignkey")
        for col in (
            "repasse_snapshot", "valor_comissao", "valor_margem", "valor_repasse_total",
            "intermediacao_status", "modelo_negocio_terceiro", "contrato_fornecedor_id", "fornecedor_id",
        ):
            op.drop_column(table, col)
    op.drop_constraint("fk_frota_veiculos_contrato_fornecedor", "frota_veiculos", type_="foreignkey")
    for col in ("exige_aprovacao_fornecedor", "publicar_site", "contrato_fornecedor_id"):
        op.drop_column("frota_veiculos", col)
    for col in (
        "margem_padrao_percentual", "contato_operacional_email", "contato_operacional_telefone",
        "contato_operacional_nome", "modelo_negocio_padrao", "locadora_parceira",
    ):
        op.drop_column("fornecedores", col)
    op.drop_table("fornecedor_contratos_precos")
    op.drop_table("fornecedor_contratos_locacao")
    op.drop_table("intermediacao_configs")
