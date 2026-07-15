"""Modelos ORM do módulo Manutenção (OS, preventiva, peças/estoque e pneus)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
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
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    CadastroStatus,
    CorretivaCausa,
    CorretivaResponsavel,
    EstoqueMovimentoTipo,
    OrdemServicoItemTipo,
    OrdemServicoOrigem,
    OrdemServicoStatus,
    OrdemServicoTipo,
    PneuPosicao,
    PneuStatus,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class ManPeca(TenantBaseModel):
    """Catálogo de peças e insumos usados nas ordens de serviço."""

    __tablename__ = "man_pecas"
    __table_args__ = (
        Index("ix_man_pecas_tenant_nome", "tenant_id", "nome"),
        Index(
            "uq_man_pecas_tenant_codigo_active",
            "tenant_id",
            "codigo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria_codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    unidade: Mapped[str] = mapped_column(String(10), nullable=False, default="UN")
    custo_medio: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "man_peca_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class ManPlanoPreventivo(TenantBaseModel):
    """Plano de manutenção preventiva por categoria/modelo de veículo."""

    __tablename__ = "man_planos_preventivos"
    __table_args__ = (Index("ix_man_planos_preventivos_tenant_nome", "tenant_id", "nome"),)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    modelo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_modelos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    intervalo_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervalo_meses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fornecedor_sugerido_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    custo_estimado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    automatico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "man_plano_preventivo_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class ManPlanoChecklist(TenantBaseModel):
    """Item de checklist vinculado a um plano preventivo."""

    __tablename__ = "man_plano_checklist"
    __table_args__ = (
        Index("ix_man_plano_checklist_plano_ordem", "plano_id", "ordem"),
    )

    plano_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_planos_preventivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ManVeiculoPlano(TenantBaseModel):
    """Vínculo veículo ↔ plano preventivo com registro da última execução."""

    __tablename__ = "man_veiculo_planos"
    __table_args__ = (
        Index(
            "uq_man_veiculo_planos_active",
            "tenant_id",
            "veiculo_id",
            "plano_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plano_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_planos_preventivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    km_ultima_execucao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_ultima_execucao: Mapped[date | None] = mapped_column(Date, nullable=True)


class ManOrdemServico(TenantBaseModel):
    """Ordem de serviço — documento central de intervenção no veículo."""

    __tablename__ = "man_ordens_servico"
    __table_args__ = (
        Index("ix_man_ordens_servico_tenant_status", "tenant_id", "status"),
        Index("ix_man_ordens_servico_tenant_veiculo", "tenant_id", "veiculo_id"),
        Index("ix_man_ordens_servico_tenant_tipo", "tenant_id", "tipo"),
        Index(
            "uq_man_ordens_servico_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[OrdemServicoTipo] = mapped_column(
        _str_enum(OrdemServicoTipo, "ordem_servico_tipo", 15),
        nullable=False,
    )
    origem: Mapped[OrdemServicoOrigem] = mapped_column(
        _str_enum(OrdemServicoOrigem, "ordem_servico_origem", 20),
        nullable=False,
        default=OrdemServicoOrigem.MANUAL,
    )
    status: Mapped[OrdemServicoStatus] = mapped_column(
        _str_enum(OrdemServicoStatus, "ordem_servico_status", 25),
        nullable=False,
        default=OrdemServicoStatus.ABERTA,
    )
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plano_preventivo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_planos_preventivos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    km_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_saida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_abertura: Mapped[date] = mapped_column(Date, nullable=False)
    data_previsao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_conclusao: Mapped[date | None] = mapped_column(Date, nullable=True)
    custo_mao_obra: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    custo_pecas: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    custo_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    requer_aprovacao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aprovado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aprovado_por_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    garantia_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    garantia_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_veiculo_anterior: Mapped[str | None] = mapped_column(String(20), nullable=True)
    causa: Mapped[CorretivaCausa | None] = mapped_column(
        _str_enum(CorretivaCausa, "corretiva_causa", 15),
        nullable=True,
    )
    responsavel_custo: Mapped[CorretivaResponsavel | None] = mapped_column(
        _str_enum(CorretivaResponsavel, "corretiva_responsavel", 15),
        nullable=True,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ManOsItem(TenantBaseModel):
    """Linha de mão de obra ou peça vinculada a uma ordem de serviço."""

    __tablename__ = "man_os_itens"
    __table_args__ = (Index("ix_man_os_itens_os_id", "os_id"),)

    os_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_ordens_servico.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_item: Mapped[OrdemServicoItemTipo] = mapped_column(
        _str_enum(OrdemServicoItemTipo, "ordem_servico_item_tipo", 15),
        nullable=False,
    )
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    peca_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_pecas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("1")
    )
    valor_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ManOsFoto(TenantBaseModel):
    """Foto da ordem de serviço (antes/depois) em storage externo."""

    __tablename__ = "man_os_fotos"
    __table_args__ = (Index("ix_man_os_fotos_os_ordem", "os_id", "ordem"),)

    os_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_ordens_servico.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    legenda: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fase: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ManEstoquePeca(TenantBaseModel):
    """Posição de estoque de uma peça por filial/almoxarifado."""

    __tablename__ = "man_estoque_pecas"
    __table_args__ = (
        Index(
            "uq_man_estoque_pecas_active",
            "tenant_id",
            "peca_id",
            "filial_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    peca_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_pecas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantidade_atual: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    quantidade_minima: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    quantidade_maxima: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    localizacao: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ManEstoqueMovimento(TenantBaseModel):
    """Movimentação de estoque de peças (entrada, saída, ajuste, transferência)."""

    __tablename__ = "man_estoque_movimentos"
    __table_args__ = (
        Index("ix_man_estoque_movimentos_peca_ocorrido", "peca_id", "ocorrido_em"),
        Index("ix_man_estoque_movimentos_filial", "filial_id"),
    )

    peca_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_pecas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filial_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tipo: Mapped[EstoqueMovimentoTipo] = mapped_column(
        _str_enum(EstoqueMovimentoTipo, "estoque_movimento_tipo", 15),
        nullable=False,
    )
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    custo_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    os_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_ordens_servico.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ManPneu(TenantBaseModel):
    """Pneu com ciclo de vida e posição no veículo."""

    __tablename__ = "man_pneus"
    __table_args__ = (
        Index("ix_man_pneus_tenant_status", "tenant_id", "status"),
        Index(
            "uq_man_pneus_tenant_numero_fogo_active",
            "tenant_id",
            "numero_fogo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    numero_fogo: Mapped[str] = mapped_column(String(50), nullable=False)
    marca: Mapped[str] = mapped_column(String(100), nullable=False)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    medida: Mapped[str] = mapped_column(String(30), nullable=False)
    veiculo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    posicao: Mapped[PneuPosicao | None] = mapped_column(
        _str_enum(PneuPosicao, "pneu_posicao", 10),
        nullable=True,
    )
    km_instalacao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_atual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vida_util_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sulco_mm: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    status: Mapped[PneuStatus] = mapped_column(
        _str_enum(PneuStatus, "pneu_status", 15),
        nullable=False,
        default=PneuStatus.NOVO,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ManPneuHistorico(TenantBaseModel):
    """Histórico de eventos do pneu (instalação, rodízio, descarte, inspeção)."""

    __tablename__ = "man_pneu_historico"
    __table_args__ = (
        Index("ix_man_pneu_historico_pneu_ocorrido", "pneu_id", "ocorrido_em"),
    )

    pneu_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("man_pneus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    veiculo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    posicao: Mapped[PneuPosicao | None] = mapped_column(
        _str_enum(PneuPosicao, "pneu_historico_posicao", 10),
        nullable=True,
    )
    km_evento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo_evento: Mapped[str] = mapped_column(String(20), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
