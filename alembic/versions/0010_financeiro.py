"""Financeiro: caixa, contas a receber/pagar, PIX, cartões, bancos, conciliação e faturamento.

Revision ID: 0010_financeiro
Revises: 0009_locacoes
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_financeiro"
down_revision: str | None = "0009_locacoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Ordem respeita dependências de chave estrangeira.
_TABLES = (
    "fin_caixa_sessoes",
    "fin_contas_bancarias",
    "fin_caixa_lancamentos",
    "fin_contas_receber",
    "fin_receber_baixas",
    "fin_contas_pagar",
    "fin_pagar_baixas",
    "fin_pix_chaves",
    "fin_pix_cobrancas",
    "fin_cartao_transacoes",
    "fin_extrato_linhas",
    "fin_faturamento_configs",
    "fin_faturas",
    "fin_fatura_titulos",
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
    # ------------------------------------------------- 9.1 Caixa (sessões)
    op.create_table(
        "fin_caixa_sessoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operador_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="aberta"),
        sa.Column("aberta_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fechada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valor_abertura", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_fechamento_informado", sa.Numeric(14, 2), nullable=True),
        sa.Column("valor_calculado", sa.Numeric(14, 2), nullable=True),
        sa.Column("divergencia", sa.Numeric(14, 2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fin_caixa_sessoes_filial_id_filiais", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operador_id"], ["users.id"],
            name="fk_fin_caixa_sessoes_operador_id_users", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_caixa_sessoes"),
    )
    op.create_index("ix_fin_caixa_sessoes_tenant_id", "fin_caixa_sessoes", ["tenant_id"])
    op.create_index("ix_fin_caixa_sessoes_tenant_status", "fin_caixa_sessoes", ["tenant_id", "status"])
    op.create_index("ix_fin_caixa_sessoes_filial_id", "fin_caixa_sessoes", ["filial_id"])
    op.create_index("ix_fin_caixa_sessoes_operador_id", "fin_caixa_sessoes", ["operador_id"])

    # ------------------------------------------------- 9.6 Contas bancárias
    op.create_table(
        "fin_contas_bancarias",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("banco_codigo", sa.String(10), nullable=False),
        sa.Column("banco_nome", sa.String(120), nullable=False),
        sa.Column("agencia", sa.String(20), nullable=False),
        sa.Column("conta", sa.String(30), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False, server_default="corrente"),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("saldo_atual", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("integracao_tipo", sa.String(10), nullable=False, server_default="manual"),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fin_contas_bancarias_filial_id_filiais", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_contas_bancarias"),
    )
    op.create_index("ix_fin_contas_bancarias_tenant_id", "fin_contas_bancarias", ["tenant_id"])
    op.create_index("ix_fin_contas_bancarias_tenant_ativa", "fin_contas_bancarias", ["tenant_id", "ativa"])
    op.create_index("ix_fin_contas_bancarias_filial_id", "fin_contas_bancarias", ["filial_id"])

    # ------------------------------------------------- 9.1 Caixa (lançamentos)
    op.create_table(
        "fin_caixa_lancamentos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("sessao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("categoria", sa.String(80), nullable=True),
        sa.Column("forma_pagamento", sa.String(20), nullable=False, server_default="dinheiro"),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("descricao", sa.String(255), nullable=True),
        sa.Column("referencia_tipo", sa.String(40), nullable=True),
        sa.Column("referencia_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["sessao_id"], ["fin_caixa_sessoes.id"],
            name="fk_fin_caixa_lancamentos_sessao_id_fin_caixa_sessoes", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_fin_caixa_lancamentos_created_by_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_caixa_lancamentos"),
    )
    op.create_index("ix_fin_caixa_lancamentos_tenant_id", "fin_caixa_lancamentos", ["tenant_id"])
    op.create_index("ix_fin_caixa_lancamentos_sessao_id", "fin_caixa_lancamentos", ["sessao_id"])
    op.create_index("ix_fin_caixa_lancamentos_tenant_tipo", "fin_caixa_lancamentos", ["tenant_id", "tipo"])

    # ------------------------------------------------- 9.2 Contas a receber
    op.create_table(
        "fin_contas_receber",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("origem", sa.String(15), nullable=False, server_default="avulso"),
        sa.Column("origem_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("valor_original", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_pago", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_saldo", sa.Numeric(14, 2), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("forma_prevista", sa.String(20), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="em_aberto"),
        sa.Column("parcela_num", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parcela_total", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("gera_pix", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_fin_contas_receber_cliente_id_clientes", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fin_contas_receber_filial_id_filiais", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_contas_receber"),
    )
    op.create_index("ix_fin_contas_receber_tenant_id", "fin_contas_receber", ["tenant_id"])
    op.create_index("ix_fin_contas_receber_tenant_status", "fin_contas_receber", ["tenant_id", "status"])
    op.create_index("ix_fin_contas_receber_cliente_id", "fin_contas_receber", ["cliente_id"])
    op.create_index("ix_fin_contas_receber_vencimento", "fin_contas_receber", ["vencimento"])
    op.create_index(
        "uq_fin_contas_receber_tenant_numero_active",
        "fin_contas_receber",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 9.2 Baixas a receber
    op.create_table(
        "fin_receber_baixas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("titulo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("forma", sa.String(20), nullable=False, server_default="dinheiro"),
        sa.Column("pago_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("caixa_lancamento_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("estornada", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("observacao", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["titulo_id"], ["fin_contas_receber.id"],
            name="fk_fin_receber_baixas_titulo_id_fin_contas_receber", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["caixa_lancamento_id"], ["fin_caixa_lancamentos.id"],
            name="fk_fin_receber_baixas_caixa_lancamento_id_fin_caixa_lancamentos",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_receber_baixas"),
    )
    op.create_index("ix_fin_receber_baixas_tenant_id", "fin_receber_baixas", ["tenant_id"])
    op.create_index("ix_fin_receber_baixas_titulo_id", "fin_receber_baixas", ["titulo_id"])

    # ------------------------------------------------- 9.3 Contas a pagar
    op.create_table(
        "fin_contas_pagar",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("origem", sa.String(15), nullable=False, server_default="avulso"),
        sa.Column("origem_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("beneficiario_nome", sa.String(160), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("valor_original", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_pago", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_saldo", sa.Numeric(14, 2), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("forma_prevista", sa.String(20), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="em_aberto"),
        sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprovado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pagamento_agendado_em", sa.Date(), nullable=True),
        sa.Column("nf_anexo_url", sa.String(500), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fornecedor_id"], ["fornecedores.id"],
            name="fk_fin_contas_pagar_fornecedor_id_fornecedores", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fin_contas_pagar_filial_id_filiais", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["aprovado_por"], ["users.id"],
            name="fk_fin_contas_pagar_aprovado_por_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_contas_pagar"),
    )
    op.create_index("ix_fin_contas_pagar_tenant_id", "fin_contas_pagar", ["tenant_id"])
    op.create_index("ix_fin_contas_pagar_tenant_status", "fin_contas_pagar", ["tenant_id", "status"])
    op.create_index("ix_fin_contas_pagar_fornecedor_id", "fin_contas_pagar", ["fornecedor_id"])
    op.create_index("ix_fin_contas_pagar_vencimento", "fin_contas_pagar", ["vencimento"])
    op.create_index(
        "uq_fin_contas_pagar_tenant_numero_active",
        "fin_contas_pagar",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 9.3 Baixas a pagar
    op.create_table(
        "fin_pagar_baixas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("titulo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("forma", sa.String(20), nullable=False, server_default="dinheiro"),
        sa.Column("pago_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("caixa_lancamento_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conta_bancaria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observacao", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["titulo_id"], ["fin_contas_pagar.id"],
            name="fk_fin_pagar_baixas_titulo_id_fin_contas_pagar", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["caixa_lancamento_id"], ["fin_caixa_lancamentos.id"],
            name="fk_fin_pagar_baixas_caixa_lancamento_id_fin_caixa_lancamentos",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conta_bancaria_id"], ["fin_contas_bancarias.id"],
            name="fk_fin_pagar_baixas_conta_bancaria_id_fin_contas_bancarias",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_pagar_baixas"),
    )
    op.create_index("ix_fin_pagar_baixas_tenant_id", "fin_pagar_baixas", ["tenant_id"])
    op.create_index("ix_fin_pagar_baixas_titulo_id", "fin_pagar_baixas", ["titulo_id"])

    # ------------------------------------------------- 9.4 PIX chaves
    op.create_table(
        "fin_pix_chaves",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conta_bancaria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("chave", sa.String(140), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("descricao", sa.String(200), nullable=True),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fin_pix_chaves_filial_id_filiais", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conta_bancaria_id"], ["fin_contas_bancarias.id"],
            name="fk_fin_pix_chaves_conta_bancaria_id_fin_contas_bancarias", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_pix_chaves"),
    )
    op.create_index("ix_fin_pix_chaves_tenant_id", "fin_pix_chaves", ["tenant_id"])
    op.create_index("ix_fin_pix_chaves_tenant_ativa", "fin_pix_chaves", ["tenant_id", "ativa"])
    op.create_index("ix_fin_pix_chaves_filial_id", "fin_pix_chaves", ["filial_id"])

    # ------------------------------------------------- 9.4 PIX cobranças
    op.create_table(
        "fin_pix_cobrancas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("titulo_receber_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chave_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("txid", sa.String(40), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("qr_code_payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="aguardando"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pago_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["titulo_receber_id"], ["fin_contas_receber.id"],
            name="fk_fin_pix_cobrancas_titulo_receber_id_fin_contas_receber", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["chave_id"], ["fin_pix_chaves.id"],
            name="fk_fin_pix_cobrancas_chave_id_fin_pix_chaves", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_pix_cobrancas"),
    )
    op.create_index("ix_fin_pix_cobrancas_tenant_id", "fin_pix_cobrancas", ["tenant_id"])
    op.create_index("ix_fin_pix_cobrancas_titulo_id", "fin_pix_cobrancas", ["titulo_receber_id"])
    op.create_index("ix_fin_pix_cobrancas_tenant_status", "fin_pix_cobrancas", ["tenant_id", "status"])
    op.create_index(
        "uq_fin_pix_cobrancas_txid_active",
        "fin_pix_cobrancas",
        ["tenant_id", "txid"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 9.5 Cartões
    op.create_table(
        "fin_cartao_transacoes",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("titulo_receber_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("gateway", sa.String(60), nullable=False, server_default="simulado"),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("parcelas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="autorizado"),
        sa.Column("taxa_adquirente", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_capturado", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("autorizacao_codigo", sa.String(40), nullable=True),
        sa.Column("capturado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contrato_id"], ["loc_contratos.id"],
            name="fk_fin_cartao_transacoes_contrato_id_loc_contratos", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["titulo_receber_id"], ["fin_contas_receber.id"],
            name="fk_fin_cartao_transacoes_titulo_receber_id_fin_contas_receber",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_cartao_transacoes"),
    )
    op.create_index("ix_fin_cartao_transacoes_tenant_id", "fin_cartao_transacoes", ["tenant_id"])
    op.create_index("ix_fin_cartao_transacoes_tenant_status", "fin_cartao_transacoes", ["tenant_id", "status"])
    op.create_index("ix_fin_cartao_transacoes_contrato_id", "fin_cartao_transacoes", ["contrato_id"])
    op.create_index("ix_fin_cartao_transacoes_titulo_id", "fin_cartao_transacoes", ["titulo_receber_id"])

    # ------------------------------------------------- 9.6 Extrato bancário
    op.create_table(
        "fin_extrato_linhas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("conta_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_movimento", sa.Date(), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("tipo", sa.String(1), nullable=False),
        sa.Column("identificador_externo", sa.String(80), nullable=True),
        sa.Column("status_conciliacao", sa.String(12), nullable=False, server_default="pendente"),
        sa.Column("match_titulo_tipo", sa.String(20), nullable=True),
        sa.Column("match_titulo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conta_id"], ["fin_contas_bancarias.id"],
            name="fk_fin_extrato_linhas_conta_id_fin_contas_bancarias", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_extrato_linhas"),
    )
    op.create_index("ix_fin_extrato_linhas_tenant_id", "fin_extrato_linhas", ["tenant_id"])
    op.create_index("ix_fin_extrato_linhas_conta_id", "fin_extrato_linhas", ["conta_id"])
    op.create_index("ix_fin_extrato_linhas_tenant_status", "fin_extrato_linhas", ["tenant_id", "status_conciliacao"])
    op.create_index("ix_fin_extrato_linhas_data_movimento", "fin_extrato_linhas", ["data_movimento"])

    # ------------------------------------------------- 9.8 Faturamento config
    op.create_table(
        "fin_faturamento_configs",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ciclo", sa.String(12), nullable=False, server_default="mensal"),
        sa.Column("dia_fechamento", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_fin_faturamento_configs_cliente_id_clientes", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_faturamento_configs"),
    )
    op.create_index("ix_fin_faturamento_configs_tenant_id", "fin_faturamento_configs", ["tenant_id"])
    op.create_index("ix_fin_faturamento_configs_cliente_id", "fin_faturamento_configs", ["cliente_id"])
    op.create_index(
        "uq_fin_faturamento_configs_cliente_active",
        "fin_faturamento_configs",
        ["tenant_id", "cliente_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 9.8 Faturas
    op.create_table(
        "fin_faturas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("emitida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vencimento", sa.Date(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="rascunho"),
        sa.Column("conta_receber_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_fin_faturas_cliente_id_clientes", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conta_receber_id"], ["fin_contas_receber.id"],
            name="fk_fin_faturas_conta_receber_id_fin_contas_receber", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_faturas"),
    )
    op.create_index("ix_fin_faturas_tenant_id", "fin_faturas", ["tenant_id"])
    op.create_index("ix_fin_faturas_tenant_status", "fin_faturas", ["tenant_id", "status"])
    op.create_index("ix_fin_faturas_cliente_id", "fin_faturas", ["cliente_id"])
    op.create_index(
        "uq_fin_faturas_tenant_numero_active",
        "fin_faturas",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 9.8 Fatura títulos
    op.create_table(
        "fin_fatura_titulos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("fatura_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo_receber_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["fatura_id"], ["fin_faturas.id"],
            name="fk_fin_fatura_titulos_fatura_id_fin_faturas", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["titulo_receber_id"], ["fin_contas_receber.id"],
            name="fk_fin_fatura_titulos_titulo_receber_id_fin_contas_receber", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fin_fatura_titulos"),
    )
    op.create_index("ix_fin_fatura_titulos_tenant_id", "fin_fatura_titulos", ["tenant_id"])
    op.create_index("ix_fin_fatura_titulos_fatura_id", "fin_fatura_titulos", ["fatura_id"])
    op.create_index(
        "uq_fin_fatura_titulos_active",
        "fin_fatura_titulos",
        ["tenant_id", "fatura_id", "titulo_receber_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table in reversed(_TABLES):
        op.drop_table(table)
