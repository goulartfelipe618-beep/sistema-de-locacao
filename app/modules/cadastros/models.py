"""Modelos ORM do módulo de Cadastros."""

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.cadastros.models_extra import (  # noqa: F401
    Fornecedor,
    Motorista,
    Parceiro,
    Vendedor,
)
from app.shared.base_model import TenantBaseModel
from app.shared.enums import ClienteDocumentoTipo, ClienteStatus, MotoristaCnhStatus, PersonType


class TabelaAuxiliar(TenantBaseModel):
    """Domínio genérico de apoio (listas de seleção) por tenant."""

    __tablename__ = "tabelas_auxiliares"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "grupo",
            "codigo",
            name="uq_tabelas_auxiliares_tenant_grupo_codigo",
        ),
        Index("ix_tabelas_auxiliares_tenant_grupo", "tenant_id", "grupo"),
    )

    grupo: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordem: Mapped[int] = mapped_column(nullable=False, default=0)
    sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Cliente(TenantBaseModel):
    """Cliente PF/PJ da locadora."""

    __tablename__ = "clientes"
    __table_args__ = (
        Index(
            "uq_clientes_tenant_cpf_active",
            "tenant_id",
            "cpf",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cpf IS NOT NULL"),
        ),
        Index(
            "uq_clientes_tenant_cnpj_active",
            "tenant_id",
            "cnpj",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cnpj IS NOT NULL"),
        ),
        Index("ix_clientes_tenant_nome", "tenant_id", "nome"),
    )

    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    person_type: Mapped[PersonType] = mapped_column(
        SAEnum(
            PersonType,
            name="person_type",
            native_enum=False,
            length=5,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[ClienteStatus] = mapped_column(
        SAEnum(
            ClienteStatus,
            name="cliente_status",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ClienteStatus.ACTIVE,
    )

    # Identificação
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(11), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    rg: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ie: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado_civil: Mapped[str | None] = mapped_column(String(40), nullable=True)
    profissao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    representante_legal: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Contato principal (contatos múltiplos em fatias futuras)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    celular: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Endereço principal
    cep: Mapped[str | None] = mapped_column(String(8), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Comercial
    categoria_codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    limite_credito: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    blacklist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motivo_bloqueio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    cnh_numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnh_categoria: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cnh_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    cnh_validade: Mapped[date | None] = mapped_column(Date, nullable=True)
    cnh_orgao: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cnh_status: Mapped[MotoristaCnhStatus] = mapped_column(
        SAEnum(
            MotoristaCnhStatus,
            name="motorista_cnh_status",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=MotoristaCnhStatus.REGULAR,
    )
    cnh_pontuacao: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Cliente nome={self.nome!r} tipo={self.person_type.value}>"


class ClienteDocumento(TenantBaseModel):
    """Arquivo anexado ao cadastro do cliente (CNH, comprovantes, etc.)."""

    __tablename__ = "cliente_documentos"
    __table_args__ = (
        Index(
            "uq_cliente_documentos_tenant_cliente_tipo_active",
            "tenant_id",
            "cliente_id",
            "tipo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_cliente_documentos_cliente_id", "cliente_id"),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[ClienteDocumentoTipo] = mapped_column(
        SAEnum(
            ClienteDocumentoTipo,
            name="cliente_documento_tipo",
            native_enum=False,
            length=30,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inline_data: Mapped[str | None] = mapped_column(Text, nullable=True)
