"""Comercial / CRM: funil, propostas, campanhas, cupons e fidelidade.

Revision ID: 0011_crm
Revises: 0010_financeiro
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_crm"
down_revision: str | None = "0010_financeiro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Ordem respeita dependências de chave estrangeira (a FK circular entre
# ``crm_campanhas`` e ``crm_cupons`` é resolvida via ALTER TABLE posterior).
_TABLES = (
    "crm_oportunidades",
    "crm_oportunidade_interacoes",
    "crm_campanhas",
    "crm_cupons",
    "crm_cupom_usos",
    "crm_propostas",
    "crm_proposta_itens",
    "crm_fidelidade_regras",
    "crm_fidelidade_tiers",
    "crm_fidelidade_contas",
    "crm_fidelidade_movimentos",
)

_FK_CAMPANHA_CUPOM = "fk_crm_campanhas_cupom_id_crm_cupons"


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
    # ------------------------------------------------- 7.1 Oportunidades
    op.create_table(
        "crm_oportunidades",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("estagio", sa.String(20), nullable=False, server_default="lead"),
        sa.Column("origem_lead", sa.String(20), nullable=False, server_default="outro"),
        sa.Column("vendedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cotacao_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposta_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valor_estimado", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("data_prevista_fechamento", sa.Date(), nullable=True),
        sa.Column("motivo_perda", sa.String(255), nullable=True),
        sa.Column("estagio_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultima_interacao_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["vendedor_id"], ["vendedores.id"],
            name="fk_crm_oportunidades_vendedor_id_vendedores", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_crm_oportunidades_cliente_id_clientes", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cotacao_id"], ["res_cotacoes.id"],
            name="fk_crm_oportunidades_cotacao_id_res_cotacoes", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reserva_id"], ["res_reservas.id"],
            name="fk_crm_oportunidades_reserva_id_res_reservas", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_oportunidades"),
    )
    op.create_index("ix_crm_oportunidades_tenant_id", "crm_oportunidades", ["tenant_id"])
    op.create_index("ix_crm_oportunidades_tenant_estagio", "crm_oportunidades", ["tenant_id", "estagio"])
    op.create_index("ix_crm_oportunidades_cliente_id", "crm_oportunidades", ["cliente_id"])
    op.create_index("ix_crm_oportunidades_cotacao_id", "crm_oportunidades", ["cotacao_id"])
    op.create_index("ix_crm_oportunidades_vendedor_id", "crm_oportunidades", ["vendedor_id"])
    op.create_index(
        "uq_crm_oportunidades_tenant_numero_active",
        "crm_oportunidades",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 7.1 Interações
    op.create_table(
        "crm_oportunidade_interacoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("oportunidade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False, server_default="nota"),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["oportunidade_id"], ["crm_oportunidades.id"],
            name="fk_crm_oportunidade_interacoes_oportunidade_id_crm_oportunidades",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_crm_oportunidade_interacoes_user_id_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_oportunidade_interacoes"),
    )
    op.create_index("ix_crm_oportunidade_interacoes_tenant_id", "crm_oportunidade_interacoes", ["tenant_id"])
    op.create_index(
        "ix_crm_oportunidade_interacoes_oportunidade_id",
        "crm_oportunidade_interacoes",
        ["oportunidade_id"],
    )

    # ------------------------------------------------- 7.3 Campanhas
    # (FK cupom_id adicionada após crm_cupons — dependência circular).
    op.create_table(
        "crm_campanhas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("inicio_em", sa.Date(), nullable=True),
        sa.Column("fim_em", sa.Date(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="rascunho"),
        sa.Column("canal", sa.String(12), nullable=False, server_default="email"),
        sa.Column("publico_alvo", sa.String(20), nullable=False, server_default="todos"),
        sa.Column("categoria_cliente", sa.String(60), nullable=True),
        sa.Column("dias_inativo", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("desconto_percentual", sa.Numeric(5, 2), nullable=True),
        sa.Column("desconto_valor", sa.Numeric(14, 2), nullable=True),
        sa.Column("cupom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("enviados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("abertos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("convertidos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mensagem_assunto", sa.String(200), nullable=True),
        sa.Column("mensagem_corpo", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_crm_campanhas"),
    )
    op.create_index("ix_crm_campanhas_tenant_id", "crm_campanhas", ["tenant_id"])
    op.create_index("ix_crm_campanhas_tenant_status", "crm_campanhas", ["tenant_id", "status"])
    op.create_index(
        "uq_crm_campanhas_tenant_codigo_active",
        "crm_campanhas",
        ["tenant_id", "codigo"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 7.4 Cupons
    op.create_table(
        "crm_cupons",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False, server_default="percentual"),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valor_minimo", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("primeira_locacao_apenas", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("inicio_em", sa.Date(), nullable=True),
        sa.Column("fim_em", sa.Date(), nullable=True),
        sa.Column("limite_uso_total", sa.Integer(), nullable=True),
        sa.Column("limite_uso_cliente", sa.Integer(), nullable=True),
        sa.Column("usos_totais", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(12), nullable=False, server_default="ativo"),
        sa.Column("campanha_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parceiro_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descricao", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["frota_categorias.id"],
            name="fk_crm_cupons_categoria_id_frota_categorias", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["campanha_id"], ["crm_campanhas.id"],
            name="fk_crm_cupons_campanha_id_crm_campanhas", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parceiro_id"], ["parceiros.id"],
            name="fk_crm_cupons_parceiro_id_parceiros", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_cupons"),
    )
    op.create_index("ix_crm_cupons_tenant_id", "crm_cupons", ["tenant_id"])
    op.create_index("ix_crm_cupons_tenant_status", "crm_cupons", ["tenant_id", "status"])
    op.create_index(
        "uq_crm_cupons_tenant_codigo_active",
        "crm_cupons",
        ["tenant_id", "codigo"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Resolve a FK circular crm_campanhas.cupom_id -> crm_cupons.id.
    op.create_foreign_key(
        _FK_CAMPANHA_CUPOM,
        "crm_campanhas",
        "crm_cupons",
        ["cupom_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------- 7.4 Uso de cupons
    op.create_table(
        "crm_cupom_usos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("cupom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("desconto_aplicado", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("usado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cupom_id"], ["crm_cupons.id"],
            name="fk_crm_cupom_usos_cupom_id_crm_cupons", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_crm_cupom_usos_cliente_id_clientes", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reserva_id"], ["res_reservas.id"],
            name="fk_crm_cupom_usos_reserva_id_res_reservas", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_cupom_usos"),
    )
    op.create_index("ix_crm_cupom_usos_tenant_id", "crm_cupom_usos", ["tenant_id"])
    op.create_index("ix_crm_cupom_usos_cupom_id", "crm_cupom_usos", ["cupom_id"])
    op.create_index("ix_crm_cupom_usos_cliente_id", "crm_cupom_usos", ["cliente_id"])

    # ------------------------------------------------- 7.2 Propostas
    op.create_table(
        "crm_propostas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("proposta_pai_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("oportunidade_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="rascunho"),
        sa.Column("validade_em", sa.Date(), nullable=True),
        sa.Column("condicoes_comerciais", sa.Text(), nullable=True),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("vendedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("campanha_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cupom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reserva_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("enviada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visualizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aceita_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["proposta_pai_id"], ["crm_propostas.id"],
            name="fk_crm_propostas_proposta_pai_id_crm_propostas", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_crm_propostas_cliente_id_clientes", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["oportunidade_id"], ["crm_oportunidades.id"],
            name="fk_crm_propostas_oportunidade_id_crm_oportunidades", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["vendedor_id"], ["vendedores.id"],
            name="fk_crm_propostas_vendedor_id_vendedores", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["campanha_id"], ["crm_campanhas.id"],
            name="fk_crm_propostas_campanha_id_crm_campanhas", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cupom_id"], ["crm_cupons.id"],
            name="fk_crm_propostas_cupom_id_crm_cupons", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reserva_id"], ["res_reservas.id"],
            name="fk_crm_propostas_reserva_id_res_reservas", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_crm_propostas_filial_id_filiais", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_propostas"),
    )
    op.create_index("ix_crm_propostas_tenant_id", "crm_propostas", ["tenant_id"])
    op.create_index("ix_crm_propostas_tenant_status", "crm_propostas", ["tenant_id", "status"])
    op.create_index("ix_crm_propostas_cliente_id", "crm_propostas", ["cliente_id"])
    op.create_index(
        "uq_crm_propostas_tenant_numero_versao_active",
        "crm_propostas",
        ["tenant_id", "numero", "versao"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 7.2 Itens da proposta
    op.create_table(
        "crm_proposta_itens",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("proposta_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("quantidade", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("periodo_inicio", sa.Date(), nullable=True),
        sa.Column("periodo_fim", sa.Date(), nullable=True),
        sa.Column("dias", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("valor_unitario", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["proposta_id"], ["crm_propostas.id"],
            name="fk_crm_proposta_itens_proposta_id_crm_propostas", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["frota_categorias.id"],
            name="fk_crm_proposta_itens_categoria_id_frota_categorias", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["veiculo_id"], ["frota_veiculos.id"],
            name="fk_crm_proposta_itens_veiculo_id_frota_veiculos", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_proposta_itens"),
    )
    op.create_index("ix_crm_proposta_itens_tenant_id", "crm_proposta_itens", ["tenant_id"])
    op.create_index("ix_crm_proposta_itens_proposta_id", "crm_proposta_itens", ["proposta_id"])

    # ------------------------------------------------- 7.5 Regras de fidelidade
    op.create_table(
        "crm_fidelidade_regras",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column(
            "nome", sa.String(120), nullable=False, server_default="Programa de Fidelidade"
        ),
        sa.Column("pontos_por_real", sa.Numeric(10, 4), nullable=False, server_default="1"),
        sa.Column("pontos_por_diaria", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("valor_por_ponto", sa.Numeric(10, 4), nullable=False, server_default="0.10"),
        sa.Column("validade_meses", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id", name="pk_crm_fidelidade_regras"),
    )
    op.create_index("ix_crm_fidelidade_regras_tenant_id", "crm_fidelidade_regras", ["tenant_id"])
    op.create_index(
        "ix_crm_fidelidade_regras_tenant_ativo", "crm_fidelidade_regras", ["tenant_id", "ativo"]
    )

    # ------------------------------------------------- 7.5 Tiers
    op.create_table(
        "crm_fidelidade_tiers",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("pontos_minimos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("beneficio_descricao", sa.String(255), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id", name="pk_crm_fidelidade_tiers"),
    )
    op.create_index("ix_crm_fidelidade_tiers_tenant_id", "crm_fidelidade_tiers", ["tenant_id"])
    op.create_index(
        "ix_crm_fidelidade_tiers_tenant_ordem", "crm_fidelidade_tiers", ["tenant_id", "ordem"]
    )

    # ------------------------------------------------- 7.5 Contas
    op.create_table(
        "crm_fidelidade_contas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pontos_saldo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pontos_historico_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_crm_fidelidade_contas_cliente_id_clientes", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tier_id"], ["crm_fidelidade_tiers.id"],
            name="fk_crm_fidelidade_contas_tier_id_crm_fidelidade_tiers", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_fidelidade_contas"),
    )
    op.create_index("ix_crm_fidelidade_contas_tenant_id", "crm_fidelidade_contas", ["tenant_id"])
    op.create_index("ix_crm_fidelidade_contas_cliente_id", "crm_fidelidade_contas", ["cliente_id"])
    op.create_index(
        "uq_crm_fidelidade_contas_cliente_active",
        "crm_fidelidade_contas",
        ["tenant_id", "cliente_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 7.5 Movimentos
    op.create_table(
        "crm_fidelidade_movimentos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("conta_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("pontos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("origem", sa.String(12), nullable=False, server_default="ajuste"),
        sa.Column("origem_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descricao", sa.String(255), nullable=True),
        sa.Column("saldo_restante", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conta_id"], ["crm_fidelidade_contas.id"],
            name="fk_crm_fidelidade_movimentos_conta_id_crm_fidelidade_contas",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crm_fidelidade_movimentos"),
    )
    op.create_index(
        "ix_crm_fidelidade_movimentos_tenant_id", "crm_fidelidade_movimentos", ["tenant_id"]
    )
    op.create_index(
        "ix_crm_fidelidade_movimentos_conta_id", "crm_fidelidade_movimentos", ["conta_id"]
    )
    op.create_index(
        "ix_crm_fidelidade_movimentos_expira_em", "crm_fidelidade_movimentos", ["expira_em"]
    )

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Remove a FK circular antes de derrubar as tabelas envolvidas.
    op.drop_constraint(_FK_CAMPANHA_CUPOM, "crm_campanhas", type_="foreignkey")

    for table in reversed(_TABLES):
        op.drop_table(table)
