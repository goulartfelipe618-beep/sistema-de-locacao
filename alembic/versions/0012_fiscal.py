"""Fiscal: NFS-e, NF-e, XML, cancelamentos e impostos (§10).

Revision ID: 0012_fiscal
Revises: 0011_crm
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_fiscal"
down_revision: str | None = "0011_crm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Ordem respeita dependências de chave estrangeira (xml_arquivos antes de
# nfse/nfe, que o referenciam).
_TABLES = (
    "fis_imposto_configs",
    "fis_aliquotas",
    "fis_xml_arquivos",
    "fis_nfse",
    "fis_nfe",
    "fis_nfe_itens",
    "fis_cancelamentos",
    "fis_prazos_cancelamento",
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
    # ------------------------------------------------- 10.5 Config tributária
    op.create_table(
        "fis_imposto_configs",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("regime", sa.String(20), nullable=False, server_default="simples_nacional"),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("nfse_automatica", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fis_imposto_configs_filial_id_filiais", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fis_imposto_configs"),
    )
    op.create_index("ix_fis_imposto_configs_tenant_id", "fis_imposto_configs", ["tenant_id"])
    op.create_index(
        "ix_fis_imposto_configs_tenant_ativo", "fis_imposto_configs", ["tenant_id", "ativo"]
    )
    op.create_index("ix_fis_imposto_configs_filial_id", "fis_imposto_configs", ["filial_id"])

    # ------------------------------------------------- 10.5 Alíquotas
    op.create_table(
        "fis_aliquotas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("servico_produto_codigo", sa.String(40), nullable=True),
        sa.Column("descricao", sa.String(200), nullable=True),
        sa.Column("aliquota_percentual", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("retencao", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["config_id"], ["fis_imposto_configs.id"],
            name="fk_fis_aliquotas_config_id_fis_imposto_configs", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fis_aliquotas"),
    )
    op.create_index("ix_fis_aliquotas_tenant_id", "fis_aliquotas", ["tenant_id"])
    op.create_index("ix_fis_aliquotas_config_id", "fis_aliquotas", ["config_id"])
    op.create_index("ix_fis_aliquotas_tenant_tipo", "fis_aliquotas", ["tenant_id", "tipo"])

    # ------------------------------------------------- 10.3 XML
    op.create_table(
        "fis_xml_arquivos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("tipo", sa.String(15), nullable=False, server_default="outro"),
        sa.Column("direcao", sa.String(10), nullable=False, server_default="emitido"),
        sa.Column("chave_acesso", sa.String(60), nullable=True),
        sa.Column("hash_sha256", sa.String(64), nullable=False),
        sa.Column("conteudo_xml", sa.Text(), nullable=False),
        sa.Column("documento_tipo", sa.String(10), nullable=True),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("periodo_ref", sa.Date(), nullable=True),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fornecedor_cnpj", sa.String(20), nullable=True),
        sa.Column("titulo_pagar_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fis_xml_arquivos_filial_id_filiais", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["titulo_pagar_id"], ["fin_contas_pagar.id"],
            name="fk_fis_xml_arquivos_titulo_pagar_id_fin_contas_pagar", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fis_xml_arquivos"),
    )
    op.create_index("ix_fis_xml_arquivos_tenant_id", "fis_xml_arquivos", ["tenant_id"])
    op.create_index("ix_fis_xml_arquivos_tenant_tipo", "fis_xml_arquivos", ["tenant_id", "tipo"])
    op.create_index("ix_fis_xml_arquivos_chave_acesso", "fis_xml_arquivos", ["chave_acesso"])
    op.create_index("ix_fis_xml_arquivos_periodo_ref", "fis_xml_arquivos", ["periodo_ref"])
    op.create_index("ix_fis_xml_arquivos_filial_id", "fis_xml_arquivos", ["filial_id"])
    op.create_index(
        "uq_fis_xml_arquivos_tenant_hash_active",
        "fis_xml_arquivos",
        ["tenant_id", "hash_sha256"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 10.1 NFS-e
    op.create_table(
        "fis_nfse",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("serie", sa.String(10), nullable=False, server_default="A"),
        sa.Column("status", sa.String(20), nullable=False, server_default="a_emitir"),
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fatura_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("municipio_ibge", sa.String(10), nullable=True),
        sa.Column("municipio_nome", sa.String(120), nullable=True),
        sa.Column("valor_servico", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("aliquota_iss", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("valor_iss", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_iss_retido", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("retencao_iss", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("discriminacao", sa.Text(), nullable=True),
        sa.Column("chave_acesso", sa.String(60), nullable=True),
        sa.Column("protocolo", sa.String(60), nullable=True),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column("xml_arquivo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("emitida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("autorizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejeicao_motivo", sa.String(255), nullable=True),
        sa.Column("provedor", sa.String(60), nullable=False, server_default="simulador"),
        sa.Column("automatica", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["contrato_id"], ["loc_contratos.id"],
            name="fk_fis_nfse_contrato_id_loc_contratos", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["fatura_id"], ["fin_faturas.id"],
            name="fk_fis_nfse_fatura_id_fin_faturas", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"],
            name="fk_fis_nfse_cliente_id_clientes", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fis_nfse_filial_id_filiais", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["xml_arquivo_id"], ["fis_xml_arquivos.id"],
            name="fk_fis_nfse_xml_arquivo_id_fis_xml_arquivos", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fis_nfse"),
    )
    op.create_index("ix_fis_nfse_tenant_id", "fis_nfse", ["tenant_id"])
    op.create_index("ix_fis_nfse_tenant_status", "fis_nfse", ["tenant_id", "status"])
    op.create_index("ix_fis_nfse_contrato_id", "fis_nfse", ["contrato_id"])
    op.create_index("ix_fis_nfse_fatura_id", "fis_nfse", ["fatura_id"])
    op.create_index("ix_fis_nfse_cliente_id", "fis_nfse", ["cliente_id"])
    op.create_index("ix_fis_nfse_filial_id", "fis_nfse", ["filial_id"])
    op.create_index(
        "uq_fis_nfse_tenant_serie_numero_active",
        "fis_nfse",
        ["tenant_id", "serie", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 10.2 NF-e
    op.create_table(
        "fis_nfe",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("serie", sa.String(10), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="a_emitir"),
        sa.Column("operacao", sa.String(15), nullable=False, server_default="venda"),
        sa.Column("destinatario_nome", sa.String(160), nullable=False),
        sa.Column("destinatario_doc", sa.String(20), nullable=True),
        sa.Column("destinatario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("natureza_operacao", sa.String(120), nullable=True),
        sa.Column("cfop_padrao", sa.String(10), nullable=True),
        sa.Column("chave_acesso", sa.String(60), nullable=True),
        sa.Column("protocolo", sa.String(60), nullable=True),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column("xml_arquivo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("emitida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("autorizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejeicao_motivo", sa.String(255), nullable=True),
        sa.Column("provedor", sa.String(60), nullable=False, server_default="simulador"),
        sa.ForeignKeyConstraint(
            ["filial_id"], ["filiais.id"],
            name="fk_fis_nfe_filial_id_filiais", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["veiculo_id"], ["frota_veiculos.id"],
            name="fk_fis_nfe_veiculo_id_frota_veiculos", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["xml_arquivo_id"], ["fis_xml_arquivos.id"],
            name="fk_fis_nfe_xml_arquivo_id_fis_xml_arquivos", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fis_nfe"),
    )
    op.create_index("ix_fis_nfe_tenant_id", "fis_nfe", ["tenant_id"])
    op.create_index("ix_fis_nfe_tenant_status", "fis_nfe", ["tenant_id", "status"])
    op.create_index("ix_fis_nfe_filial_id", "fis_nfe", ["filial_id"])
    op.create_index("ix_fis_nfe_veiculo_id", "fis_nfe", ["veiculo_id"])
    op.create_index(
        "uq_fis_nfe_tenant_serie_numero_active",
        "fis_nfe",
        ["tenant_id", "serie", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 10.2 Itens da NF-e
    op.create_table(
        "fis_nfe_itens",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nfe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("codigo", sa.String(40), nullable=True),
        sa.Column("ncm", sa.String(10), nullable=True),
        sa.Column("cfop", sa.String(10), nullable=True),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False, server_default="1"),
        sa.Column("valor_unitario", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("icms_aliquota", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("icms_valor", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("ipi_aliquota", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("ipi_valor", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("produto_ref_tipo", sa.String(20), nullable=True),
        sa.Column("produto_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["nfe_id"], ["fis_nfe.id"],
            name="fk_fis_nfe_itens_nfe_id_fis_nfe", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fis_nfe_itens"),
    )
    op.create_index("ix_fis_nfe_itens_tenant_id", "fis_nfe_itens", ["tenant_id"])
    op.create_index("ix_fis_nfe_itens_nfe_id", "fis_nfe_itens", ["nfe_id"])

    # ------------------------------------------------- 10.4 Cancelamentos
    op.create_table(
        "fis_cancelamentos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("documento_tipo", sa.String(10), nullable=False),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_evento", sa.String(15), nullable=False, server_default="cancelamento"),
        sa.Column("motivo", sa.String(255), nullable=False),
        sa.Column("justificativa_completa", sa.Text(), nullable=True),
        sa.Column("solicitado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("protocolo_retorno", sa.String(60), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="solicitado"),
        sa.Column("fora_do_prazo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_fis_cancelamentos_user_id_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fis_cancelamentos"),
    )
    op.create_index("ix_fis_cancelamentos_tenant_id", "fis_cancelamentos", ["tenant_id"])
    op.create_index(
        "ix_fis_cancelamentos_tenant_status", "fis_cancelamentos", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_fis_cancelamentos_documento",
        "fis_cancelamentos",
        ["documento_tipo", "documento_id"],
    )
    op.create_index("ix_fis_cancelamentos_user_id", "fis_cancelamentos", ["user_id"])
    op.create_index(
        "uq_fis_cancelamentos_tenant_numero_active",
        "fis_cancelamentos",
        ["tenant_id", "numero"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------- 10.4 Prazos
    op.create_table(
        "fis_prazos_cancelamento",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("tipo_documento", sa.String(10), nullable=False),
        sa.Column("uf", sa.String(2), nullable=True),
        sa.Column("municipio_ibge", sa.String(10), nullable=True),
        sa.Column("horas_limite", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("descricao", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_fis_prazos_cancelamento"),
    )
    op.create_index(
        "ix_fis_prazos_cancelamento_tenant_id", "fis_prazos_cancelamento", ["tenant_id"]
    )
    op.create_index(
        "ix_fis_prazos_cancelamento_tenant_tipo",
        "fis_prazos_cancelamento",
        ["tenant_id", "tipo_documento"],
    )
    op.create_index(
        "ix_fis_prazos_cancelamento_ativo", "fis_prazos_cancelamento", ["tenant_id", "ativo"]
    )

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table in reversed(_TABLES):
        op.drop_table(table)
