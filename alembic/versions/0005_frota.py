"""Frota: categorias, marcas, modelos, veículos, documentação e telemetria.

Revision ID: 0005_frota
Revises: 0004_cadastros_completos
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_frota"
down_revision: str | None = "0004_cadastros_completos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "frota_categorias",
    "frota_marcas",
    "frota_combustiveis",
    "frota_modelos",
    "frota_acessorios",
    "frota_veiculos",
    "frota_veiculo_acessorios",
    "frota_veiculo_fotos",
    "frota_documentos",
    "frota_telemetria_dispositivos",
    "frota_telemetria_eventos",
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
        "frota_categorias",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("capacidade_passageiros", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("capacidade_porta_malas", sa.String(60), nullable=True),
        sa.Column("transmissao_tipica", sa.String(40), nullable=True),
        sa.Column("imagem_url", sa.String(500), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grupo_tarifario", sa.String(60), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id", name="pk_frota_categorias"),
    )
    op.create_index("ix_frota_categorias_tenant_id", "frota_categorias", ["tenant_id"])
    op.create_index("ix_frota_categorias_tenant_nome", "frota_categorias", ["tenant_id", "nome"])
    op.create_index("ix_frota_categorias_tenant_ordem", "frota_categorias", ["tenant_id", "ordem"])

    op.create_table(
        "frota_marcas",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("pais_origem", sa.String(60), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id", name="pk_frota_marcas"),
    )
    op.create_index("ix_frota_marcas_tenant_id", "frota_marcas", ["tenant_id"])
    op.create_index("ix_frota_marcas_tenant_nome", "frota_marcas", ["tenant_id", "nome"])

    op.create_table(
        "frota_combustiveis",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("unidade", sa.String(10), nullable=False, server_default="litro"),
        sa.Column("preco_referencia", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id", name="pk_frota_combustiveis"),
    )
    op.create_index("ix_frota_combustiveis_tenant_id", "frota_combustiveis", ["tenant_id"])
    op.create_index(
        "ix_frota_combustiveis_tenant_nome", "frota_combustiveis", ["tenant_id", "nome"]
    )

    op.create_table(
        "frota_modelos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("marca_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_padrao_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("versao", sa.String(100), nullable=True),
        sa.Column("motorizacao", sa.String(100), nullable=True),
        sa.Column("cambio", sa.String(40), nullable=True),
        sa.Column("portas", sa.Integer(), nullable=True),
        sa.Column("capacidade_tanque", sa.Numeric(8, 2), nullable=True),
        sa.Column("consumo_medio_km_l", sa.Numeric(6, 2), nullable=True),
        sa.Column("codigo_fipe", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(
            ["marca_id"],
            ["frota_marcas.id"],
            name="fk_frota_modelos_marca_id_frota_marcas",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_padrao_id"],
            ["frota_categorias.id"],
            name="fk_frota_modelos_categoria_padrao_id_frota_categorias",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_frota_modelos"),
    )
    op.create_index("ix_frota_modelos_tenant_id", "frota_modelos", ["tenant_id"])
    op.create_index("ix_frota_modelos_marca_id", "frota_modelos", ["marca_id"])
    op.create_index(
        "ix_frota_modelos_categoria_padrao_id", "frota_modelos", ["categoria_padrao_id"]
    )
    op.create_index("ix_frota_modelos_tenant_nome", "frota_modelos", ["tenant_id", "nome"])

    op.create_table(
        "frota_acessorios",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(10), nullable=False, server_default="fixo"),
        sa.Column("valor_diaria", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estoque_disponivel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("foto_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id", name="pk_frota_acessorios"),
    )
    op.create_index("ix_frota_acessorios_tenant_id", "frota_acessorios", ["tenant_id"])
    op.create_index("ix_frota_acessorios_tenant_nome", "frota_acessorios", ["tenant_id", "nome"])

    op.create_table(
        "frota_veiculos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("placa", sa.String(10), nullable=False),
        sa.Column("renavam", sa.String(11), nullable=True),
        sa.Column("chassi", sa.String(17), nullable=True),
        sa.Column("ano_fabricacao", sa.Integer(), nullable=False),
        sa.Column("ano_modelo", sa.Integer(), nullable=False),
        sa.Column("cor", sa.String(40), nullable=True),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marca_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modelo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("combustivel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="disponivel"),
        sa.Column("propriedade", sa.String(20), nullable=False, server_default="propria"),
        sa.Column("data_compra", sa.Date(), nullable=True),
        sa.Column("valor_aquisicao", sa.Numeric(14, 2), nullable=True),
        sa.Column("km_inicial", sa.Integer(), nullable=True),
        sa.Column("km_atual", sa.Integer(), nullable=True),
        sa.Column("valor_fipe", sa.Numeric(14, 2), nullable=True),
        sa.Column("valor_mercado", sa.Numeric(14, 2), nullable=True),
        sa.Column("proprietario_nome", sa.String(200), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("motivo_bloqueio", sa.String(255), nullable=True),
        sa.Column("data_baixa", sa.Date(), nullable=True),
        sa.Column("motivo_baixa", sa.String(255), nullable=True),
        sa.Column("nivel_combustivel_atual", sa.Integer(), nullable=False, server_default="8"),
        sa.CheckConstraint(
            "nivel_combustivel_atual >= 0 AND nivel_combustivel_atual <= 8",
            name="ck_frota_veiculos_nivel_combustivel",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["frota_categorias.id"],
            name="fk_frota_veiculos_categoria_id_frota_categorias",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["marca_id"],
            ["frota_marcas.id"],
            name="fk_frota_veiculos_marca_id_frota_marcas",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["modelo_id"],
            ["frota_modelos.id"],
            name="fk_frota_veiculos_modelo_id_frota_modelos",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["combustivel_id"],
            ["frota_combustiveis.id"],
            name="fk_frota_veiculos_combustivel_id_frota_combustiveis",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["filial_id"],
            ["filiais.id"],
            name="fk_frota_veiculos_filial_id_filiais",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["fornecedor_id"],
            ["fornecedores.id"],
            name="fk_frota_veiculos_fornecedor_id_fornecedores",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_frota_veiculos"),
    )
    op.create_index("ix_frota_veiculos_tenant_id", "frota_veiculos", ["tenant_id"])
    op.create_index("ix_frota_veiculos_categoria_id", "frota_veiculos", ["categoria_id"])
    op.create_index("ix_frota_veiculos_marca_id", "frota_veiculos", ["marca_id"])
    op.create_index("ix_frota_veiculos_modelo_id", "frota_veiculos", ["modelo_id"])
    op.create_index("ix_frota_veiculos_combustivel_id", "frota_veiculos", ["combustivel_id"])
    op.create_index("ix_frota_veiculos_filial_id", "frota_veiculos", ["filial_id"])
    op.create_index("ix_frota_veiculos_fornecedor_id", "frota_veiculos", ["fornecedor_id"])
    op.create_index(
        "ix_frota_veiculos_tenant_status", "frota_veiculos", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_frota_veiculos_tenant_filial", "frota_veiculos", ["tenant_id", "filial_id"]
    )
    op.create_index(
        "uq_frota_veiculos_tenant_placa_active",
        "frota_veiculos",
        ["tenant_id", "placa"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND placa IS NOT NULL"),
    )
    op.create_index(
        "uq_frota_veiculos_tenant_renavam_active",
        "frota_veiculos",
        ["tenant_id", "renavam"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND renavam IS NOT NULL"),
    )
    op.create_index(
        "uq_frota_veiculos_tenant_chassi_active",
        "frota_veiculos",
        ["tenant_id", "chassi"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND chassi IS NOT NULL"),
    )

    op.create_table(
        "frota_veiculo_acessorios",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("acessorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_instalacao", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_frota_veiculo_acessorios_veiculo_id_frota_veiculos",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["acessorio_id"],
            ["frota_acessorios.id"],
            name="fk_frota_veiculo_acessorios_acessorio_id_frota_acessorios",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_frota_veiculo_acessorios"),
    )
    op.create_index(
        "ix_frota_veiculo_acessorios_tenant_id", "frota_veiculo_acessorios", ["tenant_id"]
    )
    op.create_index(
        "ix_frota_veiculo_acessorios_veiculo_id", "frota_veiculo_acessorios", ["veiculo_id"]
    )
    op.create_index(
        "ix_frota_veiculo_acessorios_acessorio_id", "frota_veiculo_acessorios", ["acessorio_id"]
    )
    op.create_index(
        "uq_frota_veiculo_acessorios_active",
        "frota_veiculo_acessorios",
        ["tenant_id", "veiculo_id", "acessorio_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "frota_veiculo_fotos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("legenda", sa.String(255), nullable=True),
        sa.Column("tirada_em", sa.Date(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_frota_veiculo_fotos_veiculo_id_frota_veiculos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_frota_veiculo_fotos"),
    )
    op.create_index("ix_frota_veiculo_fotos_tenant_id", "frota_veiculo_fotos", ["tenant_id"])
    op.create_index("ix_frota_veiculo_fotos_veiculo_id", "frota_veiculo_fotos", ["veiculo_id"])
    op.create_index(
        "ix_frota_veiculo_fotos_veiculo_ordem", "frota_veiculo_fotos", ["veiculo_id", "ordem"]
    )

    op.create_table(
        "frota_documentos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("numero", sa.String(60), nullable=True),
        sa.Column("orgao_emissor", sa.String(60), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=True),
        sa.Column("data_validade", sa.Date(), nullable=True),
        sa.Column("arquivo_key", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="regular"),
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_frota_documentos_veiculo_id_frota_veiculos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_frota_documentos"),
    )
    op.create_index("ix_frota_documentos_tenant_id", "frota_documentos", ["tenant_id"])
    op.create_index("ix_frota_documentos_veiculo_id", "frota_documentos", ["veiculo_id"])
    op.create_index(
        "ix_frota_documentos_veiculo_tipo", "frota_documentos", ["veiculo_id", "tipo"]
    )
    op.create_index("ix_frota_documentos_validade", "frota_documentos", ["data_validade"])

    op.create_table(
        "frota_telemetria_dispositivos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provedor", sa.String(100), nullable=False),
        sa.Column("equipamento_id", sa.String(100), nullable=False),
        sa.Column("conn_status", sa.String(20), nullable=False, server_default="offline"),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("ultima_posicao_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("km_telemetria", sa.Integer(), nullable=True),
        sa.Column(
            "bloqueio_remoto", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_frota_telemetria_dispositivos_veiculo_id_frota_veiculos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_frota_telemetria_dispositivos"),
    )
    op.create_index(
        "ix_frota_telemetria_dispositivos_tenant_id",
        "frota_telemetria_dispositivos",
        ["tenant_id"],
    )
    op.create_index(
        "ix_frota_telemetria_dispositivos_veiculo_id",
        "frota_telemetria_dispositivos",
        ["veiculo_id"],
    )
    op.create_index(
        "uq_frota_telemetria_dispositivos_veiculo_active",
        "frota_telemetria_dispositivos",
        ["tenant_id", "veiculo_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "frota_telemetria_eventos",
        _uuid_pk(),
        *_timestamps(),
        _tenant(),
        sa.Column("dispositivo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("veiculo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("velocidade", sa.Numeric(6, 2), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["dispositivo_id"],
            ["frota_telemetria_dispositivos.id"],
            name="fk_frota_tel_evt_dispositivo_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["veiculo_id"],
            ["frota_veiculos.id"],
            name="fk_frota_telemetria_eventos_veiculo_id_frota_veiculos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_frota_telemetria_eventos"),
    )
    op.create_index(
        "ix_frota_telemetria_eventos_tenant_id", "frota_telemetria_eventos", ["tenant_id"]
    )
    op.create_index(
        "ix_frota_telemetria_eventos_dispositivo_id",
        "frota_telemetria_eventos",
        ["dispositivo_id"],
    )
    op.create_index(
        "ix_frota_telemetria_eventos_veiculo_id", "frota_telemetria_eventos", ["veiculo_id"]
    )
    op.create_index(
        "ix_frota_telemetria_eventos_veiculo_ocorrido",
        "frota_telemetria_eventos",
        ["veiculo_id", "ocorrido_em"],
    )

    for table in _TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("frota_telemetria_eventos")
    op.drop_table("frota_telemetria_dispositivos")
    op.drop_table("frota_documentos")
    op.drop_table("frota_veiculo_fotos")
    op.drop_table("frota_veiculo_acessorios")
    op.drop_table("frota_veiculos")
    op.drop_table("frota_acessorios")
    op.drop_table("frota_modelos")
    op.drop_table("frota_combustiveis")
    op.drop_table("frota_marcas")
    op.drop_table("frota_categorias")
