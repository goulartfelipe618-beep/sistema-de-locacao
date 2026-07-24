"""Modelos ORM de Empresa (Tenant) e Filial."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.shared.enums import FilialStatus, TenantStatus


class Tenant(BaseModel):
    """Empresa cliente da plataforma (locadora).

    A tabela ``tenants`` é o registro-mestre do SaaS e **não** possui RLS por
    ``tenant_id`` (ela própria define os tenants); o acesso é controlado na
    camada de aplicação (apenas super-admin).
    """

    __tablename__ = "tenants"
    __table_args__ = (
        Index(
            "uq_tenants_slug_active",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_tenants_cnpj_active",
            "cnpj",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cnpj IS NOT NULL"),
        ),
    )

    slug: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    status: Mapped[TenantStatus] = mapped_column(
        SAEnum(TenantStatus, name="tenant_status", native_enum=False, length=20),
        nullable=False,
        default=TenantStatus.ACTIVE,
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    app_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    setup_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ie: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_footer_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    logo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    site_primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_background_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_header_bg_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_header_text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_topbar_bg_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_topbar_tab_bg_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_topbar_tab_text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_topbar_tab_active_bg_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_topbar_tab_active_text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_button_bg_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_button_text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_link_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_border_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_surface_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_text_muted_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_footer_bg_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_footer_text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_transition_enabled: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    site_transition_bg_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    site_transition_image_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    site_transition_image_content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    site_transition_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_transition_image_size_px: Mapped[int] = mapped_column(nullable=False, default=120, server_default="120")
    site_atendimento_webhook_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    zip_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    cert_a1_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    cert_a1_password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    cert_a1_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    cert_a1_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fiscal_emissao_habilitada: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")

    filiais: Mapped[list[Filial]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - conveniência de debug
        return f"<Tenant slug={self.slug!r} status={self.status.value}>"

    @property
    def cert_configured(self) -> bool:
        return bool(self.cert_a1_encrypted)

    @property
    def setup_complete(self) -> bool:
        return self.setup_completed_at is not None

    @property
    def sidebar_display_name(self) -> str:
        return self.app_display_name or self.trade_name or self.legal_name

    @property
    def has_logo(self) -> bool:
        return bool(self.logo_url or self.logo_storage_key)


class Filial(BaseModel):
    """Filial/unidade operacional de um tenant (loja, aeroporto, pátio)."""

    __tablename__ = "filiais"
    __table_args__ = (
        Index(
            "uq_filiais_tenant_id_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # ``tenant_id`` explícito (com FK) — esta tabela É escopada por tenant (RLS).
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    status: Mapped[FilialStatus] = mapped_column(
        SAEnum(FilialStatus, name="filial_status", native_enum=False, length=20),
        nullable=False,
        default=FilialStatus.ACTIVE,
    )
    is_headquarters: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Endereço
    zip_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    tenant: Mapped[Tenant] = relationship(back_populates="filiais")

    def __repr__(self) -> str:  # pragma: no cover - conveniência de debug
        return f"<Filial code={self.code!r} name={self.name!r}>"
