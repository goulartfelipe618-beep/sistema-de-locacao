"""Modelos ORM do módulo Tarifário (precificação e políticas)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    CadastroStatus,
    PoliticaRetencaoTipo,
    TarifarioCanal,
    TaxaAplicacao,
    TaxaCalculoTipo,
    TemporadaAjusteTipo,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class TarTabela(TenantBaseModel):
    """Tabela de tarifas por filial/canal/cliente/parceiro."""

    __tablename__ = "tar_tabelas"
    __table_args__ = (
        Index("ix_tar_tabelas_tenant_nome", "tenant_id", "nome"),
        Index("ix_tar_tabelas_tenant_vigencia", "tenant_id", "vigencia_inicio"),
        Index("ix_tar_tabelas_tenant_canal", "tenant_id", "canal"),
        Index("ix_tar_tabelas_tenant_prioridade", "tenant_id", "prioridade"),
    )

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    canal: Mapped[TarifarioCanal] = mapped_column(
        _str_enum(TarifarioCanal, "tarifario_canal", 20),
        nullable=False,
        default=TarifarioCanal.TODOS,
    )
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parceiro_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("parceiros.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prioridade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "tar_tabela_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TarTabelaItem(TenantBaseModel):
    """Valores por categoria dentro de uma tabela de tarifas."""

    __tablename__ = "tar_tabela_itens"
    __table_args__ = (
        Index(
            "uq_tar_tabela_itens_tabela_categoria_active",
            "tenant_id",
            "tabela_id",
            "categoria_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    tabela_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tar_tabelas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    valor_1_3: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_4_7: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_8_15: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_16_30: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_mensal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    km_livre: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    km_incluido: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valor_km_excedente: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)


class TarTemporada(TenantBaseModel):
    """Ajuste sazonal sobre a tabela base."""

    __tablename__ = "tar_temporadas"
    __table_args__ = (
        Index("ix_tar_temporadas_tenant_periodo", "tenant_id", "data_inicio", "data_fim"),
        Index("ix_tar_temporadas_tenant_prioridade", "tenant_id", "prioridade"),
    )

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_ajuste: Mapped[TemporadaAjusteTipo] = mapped_column(
        _str_enum(TemporadaAjusteTipo, "temporada_ajuste_tipo", 30),
        nullable=False,
    )
    valor_ajuste: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    tabela_alternativa_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tar_tabelas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    estadia_minima: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prioridade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "tar_temporada_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class TarTaxa(TenantBaseModel):
    """Taxa ou encargo adicional cobrável."""

    __tablename__ = "tar_taxas"
    __table_args__ = (Index("ix_tar_taxas_tenant_nome", "tenant_id", "nome"),)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_calculo: Mapped[TaxaCalculoTipo] = mapped_column(
        _str_enum(TaxaCalculoTipo, "taxa_calculo_tipo", 20),
        nullable=False,
    )
    valor: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    aplicacao: Mapped[TaxaAplicacao] = mapped_column(
        _str_enum(TaxaAplicacao, "taxa_aplicacao", 20),
        nullable=False,
        default=TaxaAplicacao.OPCIONAL,
    )
    regra_codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tributavel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "tar_taxa_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class TarProtecao(TenantBaseModel):
    """Proteção/seguro opcional ou obrigatório por categoria."""

    __tablename__ = "tar_protecoes"
    __table_args__ = (Index("ix_tar_protecoes_tenant_nome", "tenant_id", "nome"),)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_diaria: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    franquia: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    exclusoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    obrigatoria: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "tar_protecao_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class TarProtecaoCategoria(TenantBaseModel):
    """Categorias que exigem uma proteção obrigatória."""

    __tablename__ = "tar_protecao_categorias"
    __table_args__ = (
        Index(
            "uq_tar_protecao_categorias_active",
            "tenant_id",
            "protecao_id",
            "categoria_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    protecao_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tar_protecoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


class TarPoliticaCancelamento(TenantBaseModel):
    """Política de retenção em cancelamento/no-show."""

    __tablename__ = "tar_politicas_cancelamento"
    __table_args__ = (Index("ix_tar_politicas_cancelamento_tenant_nome", "tenant_id", "nome"),)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    canal: Mapped[TarifarioCanal] = mapped_column(
        _str_enum(TarifarioCanal, "tar_politica_canal", 20),
        nullable=False,
        default=TarifarioCanal.TODOS,
    )
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "tar_politica_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)


class TarPoliticaFaixa(TenantBaseModel):
    """Faixa de antecedência e regra de retenção."""

    __tablename__ = "tar_politica_faixas"
    __table_args__ = (
        Index("ix_tar_politica_faixas_politica_ordem", "politica_id", "ordem"),
    )

    politica_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tar_politicas_cancelamento.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    horas_antes_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    horas_antes_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo_retencao: Mapped[PoliticaRetencaoTipo] = mapped_column(
        _str_enum(PoliticaRetencaoTipo, "politica_retencao_tipo", 20),
        nullable=False,
    )
    valor_retencao: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
