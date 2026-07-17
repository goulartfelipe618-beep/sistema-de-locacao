"""Modelos ORM complementares de Cadastros (motoristas, parceiros, fornecedores, vendedores)."""

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
    MotoristaCnhStatus,
    MotoristaVinculo,
    ModeloNegocioTerceiro,
    ParceiroTipo,
    PersonType,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class Motorista(TenantBaseModel):
    """Condutor habilitado (cliente, funcionário ou terceiro)."""

    __tablename__ = "motoristas"
    __table_args__ = (
        Index("ix_motoristas_tenant_nome", "tenant_id", "nome"),
        Index(
            "uq_motoristas_tenant_cpf_active",
            "tenant_id",
            "cpf",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cpf IS NOT NULL"),
        ),
        Index(
            "uq_motoristas_tenant_cnh_active",
            "tenant_id",
            "cnh_numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cnh_numero IS NOT NULL"),
        ),
    )

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vinculo: Mapped[MotoristaVinculo] = mapped_column(
        _str_enum(MotoristaVinculo, "motorista_vinculo", 20),
        nullable=False,
        default=MotoristaVinculo.TERCEIRO,
    )
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "cadastro_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    celular: Mapped[str | None] = mapped_column(String(20), nullable=True)

    cnh_numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnh_categoria: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cnh_emissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    cnh_validade: Mapped[date | None] = mapped_column(Date, nullable=True)
    cnh_orgao: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cnh_status: Mapped[MotoristaCnhStatus] = mapped_column(
        _str_enum(MotoristaCnhStatus, "motorista_cnh_status", 20),
        nullable=False,
        default=MotoristaCnhStatus.REGULAR,
    )
    cnh_pontuacao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cnh_frente_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cnh_verso_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Parceiro(TenantBaseModel):
    """Parceiro comercial (indicação, franquia, marketplace...)."""

    __tablename__ = "parceiros"
    __table_args__ = (
        Index("ix_parceiros_tenant_nome", "tenant_id", "nome"),
        Index(
            "uq_parceiros_tenant_cpf_active",
            "tenant_id",
            "cpf",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cpf IS NOT NULL"),
        ),
        Index(
            "uq_parceiros_tenant_cnpj_active",
            "tenant_id",
            "cnpj",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cnpj IS NOT NULL"),
        ),
    )

    person_type: Mapped[PersonType] = mapped_column(
        _str_enum(PersonType, "parceiro_person_type", 5),
        nullable=False,
    )
    tipo: Mapped[ParceiroTipo] = mapped_column(
        _str_enum(ParceiroTipo, "parceiro_tipo", 20),
        nullable=False,
        default=ParceiroTipo.INDICACAO,
    )
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "parceiro_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(11), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    comissao_percentual: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    comissao_valor_fixo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    banco: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conta: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pix_chave: Mapped[str | None] = mapped_column(String(140), nullable=True)
    vigencia_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Fornecedor(TenantBaseModel):
    """Fornecedor de bens/serviços."""

    __tablename__ = "fornecedores"
    __table_args__ = (
        Index("ix_fornecedores_tenant_nome", "tenant_id", "nome"),
        Index(
            "uq_fornecedores_tenant_cnpj_active",
            "tenant_id",
            "cnpj",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cnpj IS NOT NULL"),
        ),
    )

    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "fornecedor_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    ie: Mapped[str | None] = mapped_column(String(30), nullable=True)
    categoria_codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    celular: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(8), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    banco: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conta: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pix_chave: Mapped[str | None] = mapped_column(String(140), nullable=True)
    prazo_pagamento_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    desconto_percentual: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bloqueado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motivo_bloqueio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    locadora_parceira: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    modelo_negocio_padrao: Mapped[ModeloNegocioTerceiro | None] = mapped_column(
        _str_enum(ModeloNegocioTerceiro, "fornecedor_modelo_negocio", 20),
        nullable=True,
    )
    contato_operacional_nome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contato_operacional_telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contato_operacional_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    margem_padrao_percentual: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)


class Vendedor(TenantBaseModel):
    """Vendedor/atendente interno (pode vincular a usuário do sistema)."""

    __tablename__ = "vendedores"
    __table_args__ = (
        Index("ix_vendedores_tenant_nome", "tenant_id", "nome"),
        Index(
            "uq_vendedores_tenant_usuario_active",
            "tenant_id",
            "usuario_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND usuario_id IS NOT NULL"),
        ),
    )

    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[CadastroStatus] = mapped_column(
        _str_enum(CadastroStatus, "vendedor_status", 20),
        nullable=False,
        default=CadastroStatus.ACTIVE,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    meta_contratos_mes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta_faturamento_mes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    comissao_percentual: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False, default=Decimal("0")
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
