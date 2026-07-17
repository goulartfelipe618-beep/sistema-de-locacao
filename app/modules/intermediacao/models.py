"""Modelos ORM do módulo Intermediação (locação terceirizada / locadoras parceiras)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    ContratoFornecedorStatus,
    IndisponibilidadeTerceiroMotivo,
    IntermediacaoStatus,
    ModeloNegocioTerceiro,
    ModoOperacaoLocadora,
    TipoCalculoRepasse,
    TituloStatus,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class IntermediacaoConfig(TenantBaseModel):
    """Configuração global de intermediação por tenant."""

    __tablename__ = "intermediacao_configs"
    __table_args__ = (
        Index(
            "uq_intermediacao_configs_tenant_active",
            "tenant_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    modo_operacao: Mapped[ModoOperacaoLocadora] = mapped_column(
        _str_enum(ModoOperacaoLocadora, "modo_operacao_locadora", 20),
        nullable=False,
        default=ModoOperacaoLocadora.HIBRIDA,
    )
    exige_contrato_fornecedor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    aprovar_reserva_automaticamente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    publicar_terceiros_site: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    margem_minima_percentual: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("10")
    )
    buffer_disponibilidade_horas: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    priorizar_frota_propria: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FornecedorContratoLocacao(TenantBaseModel):
    """Contrato comercial com locadora parceira (repasse ou comissão)."""

    __tablename__ = "fornecedor_contratos_locacao"
    __table_args__ = (
        Index(
            "uq_fornecedor_contratos_locacao_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fornecedor_contratos_locacao_fornecedor", "fornecedor_id"),
    )

    fornecedor_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ContratoFornecedorStatus] = mapped_column(
        _str_enum(ContratoFornecedorStatus, "contrato_fornecedor_status", 20),
        nullable=False,
        default=ContratoFornecedorStatus.RASCUNHO,
    )
    modelo_negocio: Mapped[ModeloNegocioTerceiro] = mapped_column(
        _str_enum(ModeloNegocioTerceiro, "modelo_negocio_terceiro", 20),
        nullable=False,
        default=ModeloNegocioTerceiro.REPASSE,
    )
    tipo_calculo: Mapped[TipoCalculoRepasse] = mapped_column(
        _str_enum(TipoCalculoRepasse, "tipo_calculo_repasse", 25),
        nullable=False,
        default=TipoCalculoRepasse.PERCENTUAL_RECEITA,
    )
    percentual_repasse: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    percentual_comissao: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    valor_diaria_repasse: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    margem_minima_percentual: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    prazo_pagamento_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    km_livre_dia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valor_km_excedente: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    seguro_incluso: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    documento_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    clausulas: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FornecedorContratoPreco(TenantBaseModel):
    """Tabela de precificação por categoria, filial, data e horário."""

    __tablename__ = "fornecedor_contratos_precos"
    __table_args__ = (
        Index("ix_fornecedor_contratos_precos_contrato", "contrato_fornecedor_id"),
        Index("ix_fornecedor_contratos_precos_vigencia", "vigencia_inicio", "vigencia_fim"),
    )

    contrato_fornecedor_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedor_contratos_locacao.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fim: Mapped[time | None] = mapped_column(Time, nullable=True)
    dias_minimos: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    dias_maximos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valor_cliente_diaria: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_repasse_diaria: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_hora_extra_cliente: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_hora_extra_repasse: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    percentual_comissao: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    taxa_entrega: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    prioridade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FrotaIndisponibilidadeTerceiro(TenantBaseModel):
    """Bloqueio de veículo terceirizado (locado pelo proprietário, manutenção, etc.)."""

    __tablename__ = "frota_indisponibilidade_terceiro"
    __table_args__ = (
        Index("ix_frota_indisp_terceiro_veiculo", "veiculo_id"),
        Index("ix_frota_indisp_terceiro_periodo", "inicio_em", "fim_em"),
    )

    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    inicio_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo: Mapped[IndisponibilidadeTerceiroMotivo] = mapped_column(
        _str_enum(IndisponibilidadeTerceiroMotivo, "indisp_terceiro_motivo", 30),
        nullable=False,
        default=IndisponibilidadeTerceiroMotivo.LOCADO_PELO_PROPRIETARIO,
    )
    sincronizar_site: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    registrado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class LocRepasseLancamento(TenantBaseModel):
    """Lançamento financeiro de repasse/comissão vinculado a contrato de locação."""

    __tablename__ = "loc_repasse_lancamentos"
    __table_args__ = (
        Index("ix_loc_repasse_contrato", "contrato_id"),
        Index("ix_loc_repasse_fornecedor", "fornecedor_id"),
    )

    contrato_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reserva_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contrato_fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedor_contratos_locacao.id", ondelete="SET NULL"),
        nullable=True,
    )
    modelo_negocio: Mapped[ModeloNegocioTerceiro] = mapped_column(
        _str_enum(ModeloNegocioTerceiro, "repasse_modelo_negocio", 20),
        nullable=False,
    )
    valor_cliente: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    valor_repasse: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    valor_margem: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    valor_comissao: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    conta_pagar_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_pagar.id", ondelete="SET NULL"),
        nullable=True,
    )
    conta_receber_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_receber.id", ondelete="SET NULL"),
        nullable=True,
    )
    vencimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[TituloStatus] = mapped_column(
        _str_enum(TituloStatus, "repasse_lancamento_status", 20),
        nullable=False,
        default=TituloStatus.EM_ABERTO,
    )
    repasse_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
