"""Modelos ORM do módulo Comercial / CRM (§7)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    CrmCampanhaCanal,
    CrmCampanhaPublico,
    CrmCampanhaStatus,
    CrmCupomStatus,
    CrmCupomTipo,
    CrmEstagio,
    CrmFidelidadeMovimentoTipo,
    CrmFidelidadeOrigem,
    CrmInteracaoTipo,
    CrmOrigemLead,
    CrmPropostaStatus,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


# =========================================================== 7.1 Funil de Vendas
class CrmOportunidade(TenantBaseModel):
    """Oportunidade de venda no funil comercial (§7.1)."""

    __tablename__ = "crm_oportunidades"
    __table_args__ = (
        Index(
            "uq_crm_oportunidades_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_crm_oportunidades_tenant_estagio", "tenant_id", "estagio"),
        Index("ix_crm_oportunidades_cliente_id", "cliente_id"),
        Index("ix_crm_oportunidades_cotacao_id", "cotacao_id"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    estagio: Mapped[CrmEstagio] = mapped_column(
        _str_enum(CrmEstagio, "crm_estagio", 20),
        nullable=False,
        default=CrmEstagio.LEAD,
    )
    origem_lead: Mapped[CrmOrigemLead] = mapped_column(
        _str_enum(CrmOrigemLead, "crm_origem_lead", 20),
        nullable=False,
        default=CrmOrigemLead.OUTRO,
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("vendedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cotacao_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_cotacoes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    proposta_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    reserva_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="SET NULL"),
        nullable=True,
    )
    valor_estimado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    data_prevista_fechamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    motivo_perda: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estagio_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultima_interacao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CrmOportunidadeInteracao(TenantBaseModel):
    """Interação (nota/ligação/email) registrada em uma oportunidade (§7.1)."""

    __tablename__ = "crm_oportunidade_interacoes"
    __table_args__ = (
        Index("ix_crm_oportunidade_interacoes_oportunidade_id", "oportunidade_id"),
    )

    oportunidade_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_oportunidades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[CrmInteracaoTipo] = mapped_column(
        _str_enum(CrmInteracaoTipo, "crm_interacao_tipo", 12),
        nullable=False,
        default=CrmInteracaoTipo.NOTA,
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


# =========================================================== 7.2 Propostas
class CrmProposta(TenantBaseModel):
    """Proposta comercial versionada enviada ao cliente (§7.2)."""

    __tablename__ = "crm_propostas"
    __table_args__ = (
        Index(
            "uq_crm_propostas_tenant_numero_versao_active",
            "tenant_id",
            "numero",
            "versao",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_crm_propostas_tenant_status", "tenant_id", "status"),
        Index("ix_crm_propostas_cliente_id", "cliente_id"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    proposta_pai_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_propostas.id", ondelete="SET NULL"),
        nullable=True,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    oportunidade_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_oportunidades.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[CrmPropostaStatus] = mapped_column(
        _str_enum(CrmPropostaStatus, "crm_proposta_status", 15),
        nullable=False,
        default=CrmPropostaStatus.RASCUNHO,
    )
    validade_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    condicoes_comerciais: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("vendedores.id", ondelete="SET NULL"),
        nullable=True,
    )
    campanha_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_campanhas.id", ondelete="SET NULL"),
        nullable=True,
    )
    cupom_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_cupons.id", ondelete="SET NULL"),
        nullable=True,
    )
    reserva_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="SET NULL"),
        nullable=True,
    )
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
    )
    enviada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    visualizada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aceita_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CrmPropostaItem(TenantBaseModel):
    """Linha (item) de uma proposta comercial (§7.2)."""

    __tablename__ = "crm_proposta_itens"
    __table_args__ = (Index("ix_crm_proposta_itens_proposta_id", "proposta_id"),)

    proposta_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_propostas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="SET NULL"),
        nullable=True,
    )
    veiculo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="SET NULL"),
        nullable=True,
    )
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("1")
    )
    periodo_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    periodo_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    dias: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valor_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )


# =========================================================== 7.3 Campanhas
class CrmCampanha(TenantBaseModel):
    """Campanha de marketing/relacionamento (§7.3)."""

    __tablename__ = "crm_campanhas"
    __table_args__ = (
        Index(
            "uq_crm_campanhas_tenant_codigo_active",
            "tenant_id",
            "codigo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_crm_campanhas_tenant_status", "tenant_id", "status"),
    )

    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    inicio_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    fim_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CrmCampanhaStatus] = mapped_column(
        _str_enum(CrmCampanhaStatus, "crm_campanha_status", 12),
        nullable=False,
        default=CrmCampanhaStatus.RASCUNHO,
    )
    canal: Mapped[CrmCampanhaCanal] = mapped_column(
        _str_enum(CrmCampanhaCanal, "crm_campanha_canal", 12),
        nullable=False,
        default=CrmCampanhaCanal.EMAIL,
    )
    publico_alvo: Mapped[CrmCampanhaPublico] = mapped_column(
        _str_enum(CrmCampanhaPublico, "crm_campanha_publico", 20),
        nullable=False,
        default=CrmCampanhaPublico.TODOS,
    )
    categoria_cliente: Mapped[str | None] = mapped_column(String(60), nullable=True)
    dias_inativo: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    desconto_percentual: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    desconto_valor: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    cupom_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_cupons.id", ondelete="SET NULL"),
        nullable=True,
    )
    enviados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    abertos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    convertidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mensagem_assunto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mensagem_corpo: Mapped[str | None] = mapped_column(Text, nullable=True)


# =========================================================== 7.4 Cupons
class CrmCupom(TenantBaseModel):
    """Cupom de desconto promocional (§7.4)."""

    __tablename__ = "crm_cupons"
    __table_args__ = (
        Index(
            "uq_crm_cupons_tenant_codigo_active",
            "tenant_id",
            "codigo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_crm_cupons_tenant_status", "tenant_id", "status"),
    )

    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    tipo: Mapped[CrmCupomTipo] = mapped_column(
        _str_enum(CrmCupomTipo, "crm_cupom_tipo", 12),
        nullable=False,
        default=CrmCupomTipo.PERCENTUAL,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="SET NULL"),
        nullable=True,
    )
    valor_minimo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    primeira_locacao_apenas: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    inicio_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    fim_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    limite_uso_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limite_uso_cliente: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usos_totais: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[CrmCupomStatus] = mapped_column(
        _str_enum(CrmCupomStatus, "crm_cupom_status", 12),
        nullable=False,
        default=CrmCupomStatus.ATIVO,
    )
    campanha_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_campanhas.id", ondelete="SET NULL"),
        nullable=True,
    )
    parceiro_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("parceiros.id", ondelete="SET NULL"),
        nullable=True,
    )
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CrmCupomUso(TenantBaseModel):
    """Registro de uso de um cupom por um cliente (§7.4)."""

    __tablename__ = "crm_cupom_usos"
    __table_args__ = (
        Index("ix_crm_cupom_usos_cupom_id", "cupom_id"),
        Index("ix_crm_cupom_usos_cliente_id", "cliente_id"),
    )

    cupom_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_cupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reserva_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("res_reservas.id", ondelete="SET NULL"),
        nullable=True,
    )
    desconto_aplicado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    usado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# =========================================================== 7.5 Fidelidade
class CrmFidelidadeRegra(TenantBaseModel):
    """Regra de acúmulo/validade de pontos de fidelidade (§7.5)."""

    __tablename__ = "crm_fidelidade_regras"
    __table_args__ = (Index("ix_crm_fidelidade_regras_tenant_ativo", "tenant_id", "ativo"),)

    nome: Mapped[str] = mapped_column(String(120), nullable=False, default="Programa de Fidelidade")
    pontos_por_real: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("1")
    )
    pontos_por_diaria: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0")
    )
    valor_por_ponto: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0.10")
    )
    validade_meses: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CrmFidelidadeTier(TenantBaseModel):
    """Faixa/tier do programa de fidelidade (§7.5)."""

    __tablename__ = "crm_fidelidade_tiers"
    __table_args__ = (Index("ix_crm_fidelidade_tiers_tenant_ordem", "tenant_id", "ordem"),)

    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    pontos_minimos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    beneficio_descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CrmFidelidadeConta(TenantBaseModel):
    """Conta de pontos de um cliente no programa de fidelidade (§7.5)."""

    __tablename__ = "crm_fidelidade_contas"
    __table_args__ = (
        Index(
            "uq_crm_fidelidade_contas_cliente_active",
            "tenant_id",
            "cliente_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pontos_saldo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pontos_historico_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tier_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_fidelidade_tiers.id", ondelete="SET NULL"),
        nullable=True,
    )


class CrmFidelidadeMovimento(TenantBaseModel):
    """Movimento (crédito/débito/expiração/ajuste) de pontos de fidelidade (§7.5)."""

    __tablename__ = "crm_fidelidade_movimentos"
    __table_args__ = (
        Index("ix_crm_fidelidade_movimentos_conta_id", "conta_id"),
        Index("ix_crm_fidelidade_movimentos_expira_em", "expira_em"),
    )

    conta_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("crm_fidelidade_contas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[CrmFidelidadeMovimentoTipo] = mapped_column(
        _str_enum(CrmFidelidadeMovimentoTipo, "crm_fidelidade_movimento_tipo", 12),
        nullable=False,
    )
    pontos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    origem: Mapped[CrmFidelidadeOrigem] = mapped_column(
        _str_enum(CrmFidelidadeOrigem, "crm_fidelidade_origem", 12),
        nullable=False,
        default=CrmFidelidadeOrigem.AJUSTE,
    )
    origem_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    saldo_restante: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expira_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
