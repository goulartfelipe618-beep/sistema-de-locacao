"""Modelos ORM do módulo Reservas (reservas, cotações e itens)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
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
    CotacaoStatus,
    IntermediacaoStatus,
    ModeloNegocioTerceiro,
    ReservaAlocacao,
    ReservaItemTipo,
    ReservaOrigem,
    ReservaStatus,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class ResReserva(TenantBaseModel):
    """Reserva de locação — entidade central do módulo 5."""

    __tablename__ = "res_reservas"
    __table_args__ = (
        Index(
            "uq_res_reservas_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_res_reservas_tenant_status", "tenant_id", "status"),
        Index("ix_res_reservas_tenant_retirada", "tenant_id", "retirada_em"),
        Index("ix_res_reservas_veiculo_id", "veiculo_id"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ReservaStatus] = mapped_column(
        _str_enum(ReservaStatus, "reserva_status", 20),
        nullable=False,
        default=ReservaStatus.PENDENTE,
    )
    alocacao: Mapped[ReservaAlocacao] = mapped_column(
        _str_enum(ReservaAlocacao, "reserva_alocacao", 20),
        nullable=False,
        default=ReservaAlocacao.CATEGORIA,
    )
    origem: Mapped[ReservaOrigem] = mapped_column(
        _str_enum(ReservaOrigem, "reserva_origem", 20),
        nullable=False,
        default=ReservaOrigem.BALCAO,
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    veiculo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filial_retirada_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filial_devolucao_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    retirada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    devolucao_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endereco_entrega: Mapped[str | None] = mapped_column(Text, nullable=True)

    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("vendedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parceiro_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("parceiros.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    politica_cancelamento_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tar_politicas_cancelamento.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    forma_pagamento_prevista: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cupom_codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)

    diaria_unitaria: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    dias: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_taxas: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_protecoes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_acessorios: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    desconto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    pricing_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    politica_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    motivo_cancelamento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valor_retencao: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requer_aprovacao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contrato_fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedor_contratos_locacao.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    modelo_negocio_terceiro: Mapped[ModeloNegocioTerceiro | None] = mapped_column(
        _str_enum(ModeloNegocioTerceiro, "reserva_modelo_negocio", 20),
        nullable=True,
    )
    intermediacao_status: Mapped[IntermediacaoStatus] = mapped_column(
        _str_enum(IntermediacaoStatus, "reserva_intermediacao_status", 25),
        nullable=False,
        default=IntermediacaoStatus.NAO_APLICAVEL,
    )
    valor_repasse_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_margem: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_comissao: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    repasse_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResReservaMotorista(TenantBaseModel):
    """Condutor vinculado a uma reserva."""

    __tablename__ = "res_reserva_motoristas"
    __table_args__ = (
        Index(
            "uq_res_reserva_motoristas_active",
            "tenant_id",
            "reserva_id",
            "motorista_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    reserva_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    motorista_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("motoristas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ResReservaItem(TenantBaseModel):
    """Linha de cobrança (proteção, taxa, acessório) da reserva."""

    __tablename__ = "res_reserva_itens"
    __table_args__ = (Index("ix_res_reserva_itens_reserva_id", "reserva_id"),)

    reserva_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[ReservaItemTipo] = mapped_column(
        _str_enum(ReservaItemTipo, "reserva_item_tipo", 20),
        nullable=False,
    )
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("1")
    )
    valor_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )


class ResCotacao(TenantBaseModel):
    """Cotação/orçamento sem compromisso de disponibilidade."""

    __tablename__ = "res_cotacoes"
    __table_args__ = (
        Index(
            "uq_res_cotacoes_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_res_cotacoes_tenant_status", "tenant_id", "status"),
        Index("ix_res_cotacoes_validade", "validade_em"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[CotacaoStatus] = mapped_column(
        _str_enum(CotacaoStatus, "cotacao_status", 20),
        nullable=False,
        default=CotacaoStatus.ABERTA,
    )
    validade_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    filial_retirada_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filial_devolucao_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    veiculo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="SET NULL"),
        nullable=True,
    )
    retirada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    devolucao_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    converted_reserva_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    origem: Mapped[ReservaOrigem] = mapped_column(
        _str_enum(ReservaOrigem, "cotacao_origem", 20),
        nullable=False,
        default=ReservaOrigem.BALCAO,
    )
    parceiro_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("parceiros.id", ondelete="SET NULL"),
        nullable=True,
    )

    diaria_unitaria: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    dias: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_taxas: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_protecoes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    total_acessorios: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    desconto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    pricing_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
