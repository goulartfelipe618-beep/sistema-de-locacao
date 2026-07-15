"""Modelos ORM do módulo Fiscal (§10)."""

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
    CancelamentoEventoTipo,
    CancelamentoStatus,
    FiscalDocumentoTipo,
    FiscalXmlDirecao,
    FiscalXmlTipo,
    ImpostoTipo,
    NfeOperacao,
    NfeStatus,
    NfseStatus,
    RegimeTributario,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


# =========================================================== 10.5 Impostos
class FisImpostoConfig(TenantBaseModel):
    """Configuração de regime tributário por filial (ou padrão do tenant) (§10.5)."""

    __tablename__ = "fis_imposto_configs"
    __table_args__ = (
        Index("ix_fis_imposto_configs_tenant_ativo", "tenant_id", "ativo"),
        Index("ix_fis_imposto_configs_filial_id", "filial_id"),
    )

    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    regime: Mapped[RegimeTributario] = mapped_column(
        _str_enum(RegimeTributario, "regime_tributario", 20),
        nullable=False,
        default=RegimeTributario.SIMPLES_NACIONAL,
    )
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    nfse_automatica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FisAliquota(TenantBaseModel):
    """Alíquota tributária vinculada a uma configuração fiscal (§10.5)."""

    __tablename__ = "fis_aliquotas"
    __table_args__ = (
        Index("ix_fis_aliquotas_config_id", "config_id"),
        Index("ix_fis_aliquotas_tenant_tipo", "tenant_id", "tipo"),
    )

    config_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fis_imposto_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[ImpostoTipo] = mapped_column(
        _str_enum(ImpostoTipo, "imposto_tipo", 10),
        nullable=False,
    )
    servico_produto_codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    aliquota_percentual: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    retencao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)


# =========================================================== 10.3 XML
class FisXmlArquivo(TenantBaseModel):
    """Arquivo XML fiscal arquivado (emitido/recebido) (§10.3)."""

    __tablename__ = "fis_xml_arquivos"
    __table_args__ = (
        Index(
            "uq_fis_xml_arquivos_tenant_hash_active",
            "tenant_id",
            "hash_sha256",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fis_xml_arquivos_tenant_tipo", "tenant_id", "tipo"),
        Index("ix_fis_xml_arquivos_chave_acesso", "chave_acesso"),
        Index("ix_fis_xml_arquivos_periodo_ref", "periodo_ref"),
        Index("ix_fis_xml_arquivos_filial_id", "filial_id"),
    )

    tipo: Mapped[FiscalXmlTipo] = mapped_column(
        _str_enum(FiscalXmlTipo, "fiscal_xml_tipo", 15),
        nullable=False,
        default=FiscalXmlTipo.OUTRO,
    )
    direcao: Mapped[FiscalXmlDirecao] = mapped_column(
        _str_enum(FiscalXmlDirecao, "fiscal_xml_direcao", 10),
        nullable=False,
        default=FiscalXmlDirecao.EMITIDO,
    )
    chave_acesso: Mapped[str | None] = mapped_column(String(60), nullable=True)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    conteudo_xml: Mapped[str] = mapped_column(Text, nullable=False)
    documento_tipo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    documento_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    periodo_ref: Mapped[date | None] = mapped_column(Date, nullable=True)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fornecedor_cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    titulo_pagar_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_contas_pagar.id", ondelete="SET NULL"),
        nullable=True,
    )


# =========================================================== 10.1 NFS-e
class FisNfse(TenantBaseModel):
    """Nota Fiscal de Serviço Eletrônica (§10.1)."""

    __tablename__ = "fis_nfse"
    __table_args__ = (
        Index(
            "uq_fis_nfse_tenant_serie_numero_active",
            "tenant_id",
            "serie",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fis_nfse_tenant_status", "tenant_id", "status"),
        Index("ix_fis_nfse_contrato_id", "contrato_id"),
        Index("ix_fis_nfse_fatura_id", "fatura_id"),
        Index("ix_fis_nfse_cliente_id", "cliente_id"),
        Index("ix_fis_nfse_filial_id", "filial_id"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    serie: Mapped[str] = mapped_column(String(10), nullable=False, default="A")
    status: Mapped[NfseStatus] = mapped_column(
        _str_enum(NfseStatus, "nfse_status", 20),
        nullable=False,
        default=NfseStatus.A_EMITIR,
    )
    contrato_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("loc_contratos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fatura_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fin_faturas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    municipio_ibge: Mapped[str | None] = mapped_column(String(10), nullable=True)
    municipio_nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    valor_servico: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    aliquota_iss: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    valor_iss: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_iss_retido: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    retencao_iss: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discriminacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    chave_acesso: Mapped[str | None] = mapped_column(String(60), nullable=True)
    protocolo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    xml_arquivo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fis_xml_arquivos.id", ondelete="SET NULL"),
        nullable=True,
    )
    emitida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    autorizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejeicao_motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provedor: Mapped[str] = mapped_column(String(60), nullable=False, default="simulador")
    automatica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# =========================================================== 10.2 NF-e
class FisNfe(TenantBaseModel):
    """Nota Fiscal Eletrônica de produtos/mercadorias (§10.2)."""

    __tablename__ = "fis_nfe"
    __table_args__ = (
        Index(
            "uq_fis_nfe_tenant_serie_numero_active",
            "tenant_id",
            "serie",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fis_nfe_tenant_status", "tenant_id", "status"),
        Index("ix_fis_nfe_filial_id", "filial_id"),
        Index("ix_fis_nfe_veiculo_id", "veiculo_id"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    serie: Mapped[str] = mapped_column(String(10), nullable=False, default="1")
    status: Mapped[NfeStatus] = mapped_column(
        _str_enum(NfeStatus, "nfe_status", 20),
        nullable=False,
        default=NfeStatus.A_EMITIR,
    )
    operacao: Mapped[NfeOperacao] = mapped_column(
        _str_enum(NfeOperacao, "nfe_operacao", 15),
        nullable=False,
        default=NfeOperacao.VENDA,
    )
    destinatario_nome: Mapped[str] = mapped_column(String(160), nullable=False)
    destinatario_doc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    destinatario_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    filial_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    veiculo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    natureza_operacao: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cfop_padrao: Mapped[str | None] = mapped_column(String(10), nullable=True)
    chave_acesso: Mapped[str | None] = mapped_column(String(60), nullable=True)
    protocolo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    xml_arquivo_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fis_xml_arquivos.id", ondelete="SET NULL"),
        nullable=True,
    )
    emitida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    autorizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejeicao_motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provedor: Mapped[str] = mapped_column(String(60), nullable=False, default="simulador")


class FisNfeItem(TenantBaseModel):
    """Item de uma NF-e (§10.2)."""

    __tablename__ = "fis_nfe_itens"
    __table_args__ = (Index("ix_fis_nfe_itens_nfe_id", "nfe_id"),)

    nfe_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fis_nfe.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ncm: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cfop: Mapped[str | None] = mapped_column(String(10), nullable=True)
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("1")
    )
    valor_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    icms_aliquota: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    icms_valor: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    ipi_aliquota: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    ipi_valor: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    produto_ref_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    produto_ref_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)


# =========================================================== 10.4 Cancelamentos
class FisCancelamento(TenantBaseModel):
    """Evento fiscal de cancelamento/carta de correção/inutilização (§10.4)."""

    __tablename__ = "fis_cancelamentos"
    __table_args__ = (
        Index(
            "uq_fis_cancelamentos_tenant_numero_active",
            "tenant_id",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_fis_cancelamentos_tenant_status", "tenant_id", "status"),
        Index("ix_fis_cancelamentos_documento", "documento_tipo", "documento_id"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    documento_tipo: Mapped[FiscalDocumentoTipo] = mapped_column(
        _str_enum(FiscalDocumentoTipo, "fiscal_documento_tipo", 10),
        nullable=False,
    )
    documento_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    tipo_evento: Mapped[CancelamentoEventoTipo] = mapped_column(
        _str_enum(CancelamentoEventoTipo, "cancelamento_evento_tipo", 15),
        nullable=False,
        default=CancelamentoEventoTipo.CANCELAMENTO,
    )
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    justificativa_completa: Mapped[str | None] = mapped_column(Text, nullable=True)
    solicitado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    protocolo_retorno: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[CancelamentoStatus] = mapped_column(
        _str_enum(CancelamentoStatus, "cancelamento_status", 12),
        nullable=False,
        default=CancelamentoStatus.SOLICITADO,
    )
    fora_do_prazo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class FisPrazoCancelamento(TenantBaseModel):
    """Prazo legal parametrizável de cancelamento por tipo/UF/município (§10.4)."""

    __tablename__ = "fis_prazos_cancelamento"
    __table_args__ = (
        Index("ix_fis_prazos_cancelamento_tenant_tipo", "tenant_id", "tipo_documento"),
        Index("ix_fis_prazos_cancelamento_ativo", "tenant_id", "ativo"),
    )

    tipo_documento: Mapped[FiscalDocumentoTipo] = mapped_column(
        _str_enum(FiscalDocumentoTipo, "fiscal_documento_tipo", 10),
        nullable=False,
    )
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    municipio_ibge: Mapped[str | None] = mapped_column(String(10), nullable=True)
    horas_limite: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
