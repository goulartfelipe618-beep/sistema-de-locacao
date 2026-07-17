"""Modelos ORM do módulo Frota (veículos e cadastros mestres)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
    AcessorioTipo,
    CadastroStatus,
    CombustivelUnidade,
    DocumentoVeiculoStatus,
    DocumentoVeiculoTipo,
    TelemetriaConnStatus,
    TelemetriaEventoTipo,
    VeiculoPropriedade,
    VeiculoStatus,
)

def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class FrotaCategoria(TenantBaseModel):
    """Categoria comercial de veículos (Econômico, SUV, Executivo...)."""

    __tablename__ = "frota_categorias"
    __table_args__ = (
        Index("ix_frota_categorias_tenant_nome", "tenant_id", "nome"),
        Index("ix_frota_categorias_tenant_ordem", "tenant_id", "ordem"),
    )

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacidade_passageiros: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    capacidade_porta_malas: Mapped[str | None] = mapped_column(String(60), nullable=True)
    transmissao_tipica: Mapped[str | None] = mapped_column(String(40), nullable=True)
    imagem_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grupo_tarifario: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "frota_categoria_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class FrotaMarca(TenantBaseModel):
    """Montadora / marca de veículo."""

    __tablename__ = "frota_marcas"
    __table_args__ = (Index("ix_frota_marcas_tenant_nome", "tenant_id", "nome"),)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pais_origem: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "frota_marca_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class FrotaCombustivel(TenantBaseModel):
    """Tipo de combustível/energia (Gasolina, Flex, Elétrico...)."""

    __tablename__ = "frota_combustiveis"
    __table_args__ = (Index("ix_frota_combustiveis_tenant_nome", "tenant_id", "nome"),)

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    unidade: Mapped[CombustivelUnidade] = mapped_column(
        _str_enum(CombustivelUnidade, "combustivel_unidade", 10),
        nullable=False,
        default=CombustivelUnidade.LITRO,
    )
    preco_referencia: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "frota_combustivel_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class FrotaModelo(TenantBaseModel):
    """Modelo/versão vinculado a uma marca."""

    __tablename__ = "frota_modelos"
    __table_args__ = (Index("ix_frota_modelos_tenant_nome", "tenant_id", "nome"),)

    marca_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_marcas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    categoria_padrao_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    versao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    motorizacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cambio: Mapped[str | None] = mapped_column(String(40), nullable=True)
    portas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacidade_tanque: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    consumo_medio_km_l: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    codigo_fipe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "frota_modelo_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class FrotaAcessorio(TenantBaseModel):
    """Catálogo de acessórios fixos ou avulsos locáveis."""

    __tablename__ = "frota_acessorios"
    __table_args__ = (Index("ix_frota_acessorios_tenant_nome", "tenant_id", "nome"),)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[AcessorioTipo] = mapped_column(
        _str_enum(AcessorioTipo, "acessorio_tipo", 10),
        nullable=False,
        default=AcessorioTipo.FIXO,
    )
    valor_diaria: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    estoque_disponivel: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "frota_acessorio_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )


class FrotaVeiculo(TenantBaseModel):
    """Veículo da frota — núcleo operacional."""

    __tablename__ = "frota_veiculos"
    __table_args__ = (
        Index("ix_frota_veiculos_tenant_status", "tenant_id", "status"),
        Index("ix_frota_veiculos_tenant_filial", "tenant_id", "filial_id"),
        Index(
            "uq_frota_veiculos_tenant_placa_active",
            "tenant_id",
            "placa",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND placa IS NOT NULL"),
        ),
        Index(
            "uq_frota_veiculos_tenant_renavam_active",
            "tenant_id",
            "renavam",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND renavam IS NOT NULL"),
        ),
        Index(
            "uq_frota_veiculos_tenant_chassi_active",
            "tenant_id",
            "chassi",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND chassi IS NOT NULL"),
        ),
        CheckConstraint(
            "nivel_combustivel_atual >= 0 AND nivel_combustivel_atual <= 8",
            name="ck_frota_veiculos_nivel_combustivel",
        ),
    )

    placa: Mapped[str] = mapped_column(String(10), nullable=False)
    renavam: Mapped[str | None] = mapped_column(String(11), nullable=True)
    chassi: Mapped[str | None] = mapped_column(String(17), nullable=True)
    ano_fabricacao: Mapped[int] = mapped_column(Integer, nullable=False)
    ano_modelo: Mapped[int] = mapped_column(Integer, nullable=False)
    cor: Mapped[str | None] = mapped_column(String(40), nullable=True)

    categoria_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    marca_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_marcas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    modelo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_modelos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    combustivel_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_combustiveis.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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

    status: Mapped[VeiculoStatus] = mapped_column(
        _str_enum(VeiculoStatus, "veiculo_status", 20),
        nullable=False,
        default=VeiculoStatus.DISPONIVEL,
    )
    propriedade: Mapped[VeiculoPropriedade] = mapped_column(
        _str_enum(VeiculoPropriedade, "veiculo_propriedade", 20),
        nullable=False,
        default=VeiculoPropriedade.PROPRIA,
    )

    data_compra: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_aquisicao: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    km_inicial: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_atual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valor_fipe: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_mercado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    proprietario_nome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    motivo_bloqueio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_baixa: Mapped[date | None] = mapped_column(Date, nullable=True)
    motivo_baixa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nivel_combustivel_atual: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    publicar_site: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exige_aprovacao_fornecedor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FrotaVeiculoAcessorio(TenantBaseModel):
    """Vínculo de acessório instalado em um veículo."""

    __tablename__ = "frota_veiculo_acessorios"
    __table_args__ = (
        Index(
            "uq_frota_veiculo_acessorios_active",
            "tenant_id",
            "veiculo_id",
            "acessorio_id",
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
    acessorio_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_acessorios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    data_instalacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FrotaVeiculoFoto(TenantBaseModel):
    """Foto do veículo (storage externo via storage_key)."""

    __tablename__ = "frota_veiculo_fotos"
    __table_args__ = (Index("ix_frota_veiculo_fotos_veiculo_ordem", "veiculo_id", "ordem"),)

    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    legenda: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tirada_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FrotaDocumento(TenantBaseModel):
    """Documento obrigatório com vigência por veículo."""

    __tablename__ = "frota_documentos"
    __table_args__ = (
        Index("ix_frota_documentos_veiculo_tipo", "veiculo_id", "tipo"),
        Index("ix_frota_documentos_validade", "data_validade"),
    )

    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[DocumentoVeiculoTipo] = mapped_column(
        _str_enum(DocumentoVeiculoTipo, "documento_veiculo_tipo", 30),
        nullable=False,
    )
    numero: Mapped[str | None] = mapped_column(String(60), nullable=True)
    orgao_emissor: Mapped[str | None] = mapped_column(String(60), nullable=True)
    data_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_validade: Mapped[date | None] = mapped_column(Date, nullable=True)
    arquivo_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[DocumentoVeiculoStatus] = mapped_column(
        _str_enum(DocumentoVeiculoStatus, "documento_veiculo_status", 20),
        nullable=False,
        default=DocumentoVeiculoStatus.REGULAR,
    )
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FrotaTelemetriaDispositivo(TenantBaseModel):
    """Rastreador/telemetria vinculado a um veículo (1:1 ativo)."""

    __tablename__ = "frota_telemetria_dispositivos"
    __table_args__ = (
        Index(
            "uq_frota_telemetria_dispositivos_veiculo_active",
            "tenant_id",
            "veiculo_id",
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
    provedor: Mapped[str] = mapped_column(String(100), nullable=False)
    equipamento_id: Mapped[str] = mapped_column(String(100), nullable=False)
    conn_status: Mapped[TelemetriaConnStatus] = mapped_column(
        _str_enum(TelemetriaConnStatus, "telemetria_conn_status", 20),
        nullable=False,
        default=TelemetriaConnStatus.OFFLINE,
    )
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    ultima_posicao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    km_telemetria: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bloqueio_remoto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FrotaTelemetriaEvento(TenantBaseModel):
    """Evento de telemetria/condução registrado pelo rastreador."""

    __tablename__ = "frota_telemetria_eventos"
    __table_args__ = (
        Index("ix_frota_telemetria_eventos_veiculo_ocorrido", "veiculo_id", "ocorrido_em"),
        Index("ix_frota_telemetria_eventos_dispositivo", "dispositivo_id"),
    )

    dispositivo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_telemetria_dispositivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    veiculo_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("frota_veiculos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[TelemetriaEventoTipo] = mapped_column(
        _str_enum(TelemetriaEventoTipo, "telemetria_evento_tipo", 30),
        nullable=False,
    )
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    velocidade: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
