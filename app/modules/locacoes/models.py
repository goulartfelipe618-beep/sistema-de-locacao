"""Modelos ORM do módulo Locações (contratos, vistorias, avarias e multas)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
    AvariaOrigem,
    AvariaResponsabilidade,
    AvariaSeveridade,
    AvariaStatus,
    ContratoCondicaoPagamento,
    ContratoStatus,
    MultaStatus,
    ReservaItemTipo,
    VistoriaTipo,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class LocContrato(TenantBaseModel):
    """Contrato de locação — entidade central do módulo 6."""

    __tablename__ = "loc_contratos"
    __table_args__ = (
        Index(
            "uq_loc_contratos_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_loc_contratos_tenant_status", "tenant_id", "status"),
        Index("ix_loc_contratos_veiculo_id", "veiculo_id"),
        Index("ix_loc_contratos_cliente_id", "cliente_id"),
        Index("ix_loc_contratos_reserva_id", "reserva_id"),
        CheckConstraint(
            "combustivel_saida IS NULL OR (combustivel_saida >= 0 AND combustivel_saida <= 8)",
            name="ck_loc_contratos_combustivel_saida",
        ),
        CheckConstraint(
            "combustivel_entrada IS NULL OR (combustivel_entrada >= 0 AND combustivel_entrada <= 8)",
            name="ck_loc_contratos_combustivel_entrada",
        ),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ContratoStatus] = mapped_column(
        _str_enum(ContratoStatus, "contrato_status", 25),
        nullable=False,
        default=ContratoStatus.RASCUNHO,
    )

    reserva_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="RESTRICT"),
        nullable=False,
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

    retirada_prevista_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    devolucao_prevista_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    checkout_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checkin_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    km_saida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    combustivel_saida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    combustivel_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
    caucao: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    ajustes_checkin: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_final: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    forma_pagamento: Mapped[str | None] = mapped_column(String(60), nullable=True)
    condicao: Mapped[ContratoCondicaoPagamento] = mapped_column(
        _str_enum(ContratoCondicaoPagamento, "contrato_condicao_pagamento", 25),
        nullable=False,
        default=ContratoCondicaoPagamento.AVISTA,
    )

    pricing_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    politica_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    clausulas_combustivel: Mapped[str | None] = mapped_column(Text, nullable=True)

    assinatura_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assinatura_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pendencia_financeira: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class LocContratoMotorista(TenantBaseModel):
    """Condutor autorizado no contrato."""

    __tablename__ = "loc_contrato_motoristas"
    __table_args__ = (
        Index(
            "uq_loc_contrato_motoristas_active",
            "tenant_id",
            "contrato_id",
            "motorista_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    contrato_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="CASCADE"),
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


class LocContratoItem(TenantBaseModel):
    """Linha de cobrança do contrato (proteção, taxa, acessório)."""

    __tablename__ = "loc_contrato_itens"
    __table_args__ = (Index("ix_loc_contrato_itens_contrato_id", "contrato_id"),)

    contrato_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[ReservaItemTipo] = mapped_column(
        _str_enum(ReservaItemTipo, "loc_contrato_item_tipo", 20),
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


class LocContratoAditivo(TenantBaseModel):
    """Aditivo de renovação vinculado ao contrato original."""

    __tablename__ = "loc_contrato_aditivos"
    __table_args__ = (
        Index("ix_loc_contrato_aditivos_contrato_id", "contrato_id"),
        Index("ix_loc_contrato_aditivos_tenant_contrato", "tenant_id", "contrato_id"),
    )

    contrato_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    devolucao_anterior: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    devolucao_nova: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    dias_extra: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_aditivo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    pricing_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    aprovado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)


class LocVistoria(TenantBaseModel):
    """Vistoria de check-out ou check-in."""

    __tablename__ = "loc_vistorias"
    __table_args__ = (
        Index("ix_loc_vistorias_contrato_id", "contrato_id"),
        Index("ix_loc_vistorias_tenant_tipo", "tenant_id", "tipo"),
        CheckConstraint(
            "combustivel_nivel >= 0 AND combustivel_nivel <= 8",
            name="ck_loc_vistorias_combustivel_nivel",
        ),
    )

    contrato_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[VistoriaTipo] = mapped_column(
        _str_enum(VistoriaTipo, "vistoria_tipo", 15),
        nullable=False,
    )
    km: Mapped[int] = mapped_column(Integer, nullable=False)
    combustivel_nivel: Mapped[int] = mapped_column(Integer, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    realizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    realizado_por_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    checklist_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class LocVistoriaFoto(TenantBaseModel):
    """Foto vinculada a uma vistoria."""

    __tablename__ = "loc_vistoria_fotos"
    __table_args__ = (Index("ix_loc_vistoria_fotos_vistoria_id", "vistoria_id"),)

    vistoria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_vistorias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    angulo: Mapped[str] = mapped_column(String(30), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LocAvaria(TenantBaseModel):
    """Registro de avaria/dano identificado em vistoria ou sinistro."""

    __tablename__ = "loc_avarias"
    __table_args__ = (
        Index("ix_loc_avarias_veiculo_id", "veiculo_id"),
        Index("ix_loc_avarias_contrato_id", "contrato_id"),
        Index("ix_loc_avarias_tenant_status", "tenant_id", "status"),
    )

    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contrato_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vistoria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_vistorias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    origem: Mapped[AvariaOrigem] = mapped_column(
        _str_enum(AvariaOrigem, "avaria_origem", 15),
        nullable=False,
    )
    localizacao: Mapped[str] = mapped_column(String(100), nullable=False)
    severidade: Mapped[AvariaSeveridade] = mapped_column(
        _str_enum(AvariaSeveridade, "avaria_severidade", 10),
        nullable=False,
    )
    responsabilidade: Mapped[AvariaResponsabilidade | None] = mapped_column(
        _str_enum(AvariaResponsabilidade, "avaria_responsabilidade", 15),
        nullable=True,
    )
    laudo: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_reparo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[AvariaStatus] = mapped_column(
        _str_enum(AvariaStatus, "avaria_status", 30),
        nullable=False,
        default=AvariaStatus.REGISTRADA,
    )
    os_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_ordens_servico.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class LocAvariaFoto(TenantBaseModel):
    """Foto vinculada a uma avaria."""

    __tablename__ = "loc_avaria_fotos"
    __table_args__ = (Index("ix_loc_avaria_fotos_avaria_id", "avaria_id"),)

    avaria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_avarias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    legenda: Mapped[str | None] = mapped_column(String(200), nullable=True)


class LocMulta(TenantBaseModel):
    """Multa de trânsito vinculada a veículo/contrato."""

    __tablename__ = "loc_multas"
    __table_args__ = (
        Index("ix_loc_multas_veiculo_id", "veiculo_id"),
        Index("ix_loc_multas_contrato_id", "contrato_id"),
        Index("ix_loc_multas_tenant_status", "tenant_id", "status"),
        Index("ix_loc_multas_ocorrido_em", "ocorrido_em"),
    )

    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contrato_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    motorista_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("motoristas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    orgao: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo_infracao: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    pontuacao: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ait: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[MultaStatus] = mapped_column(
        _str_enum(MultaStatus, "multa_status", 15),
        nullable=False,
        default=MultaStatus.RECEBIDA,
    )
    taxa_admin: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
