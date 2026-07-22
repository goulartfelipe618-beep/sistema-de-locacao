"""Modelos ORM do módulo Integrações (§12)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    IntegracaoConsultaStatus,
    IntegracaoConsultaTipo,
    IntegracaoProvedorStatus,
    IntegracaoTipo,
    WebhookEventoStatus,
)


def _str_enum(enum_cls: type, name: str, length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda items: [item.value for item in items],
    )


class IntProvedorConfig(TenantBaseModel):
    """Configuração de provedor externo por tenant/filial (§12)."""

    __tablename__ = "int_provedor_configs"
    __table_args__ = (
        Index("ix_int_prov_cfg_tenant_tipo", "tenant_id", "tipo"),
        Index("ix_int_prov_cfg_webhook_token", "webhook_token", unique=True),
    )

    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
    )
    tipo: Mapped[IntegracaoTipo] = mapped_column(
        _str_enum(IntegracaoTipo, "int_tipo", 15),
        nullable=False,
    )
    provedor: Mapped[str] = mapped_column(String(60), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    credenciais_cripto: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret_cripto: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_token: Mapped[str] = mapped_column(String(64), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[IntegracaoProvedorStatus] = mapped_column(
        _str_enum(IntegracaoProvedorStatus, "int_prov_status", 10),
        nullable=False,
        default=IntegracaoProvedorStatus.ATIVO,
    )
    ultimo_sync_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultimo_erro: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntWebhookEvento(TenantBaseModel):
    """Log de eventos webhook recebidos (§12.1)."""

    __tablename__ = "int_webhook_eventos"
    __table_args__ = (Index("ix_int_webhook_tenant_status", "tenant_id", "status"),)

    config_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("int_provedor_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    provedor: Mapped[str] = mapped_column(String(60), nullable=False)
    evento_tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    assinatura_valida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[WebhookEventoStatus] = mapped_column(
        _str_enum(WebhookEventoStatus, "int_webhook_status", 12),
        nullable=False,
        default=WebhookEventoStatus.RECEBIDO,
    )
    processado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntConsulta(TenantBaseModel):
    """Histórico de consultas externas (DETRAN, crédito)."""

    __tablename__ = "int_consultas"
    __table_args__ = (Index("ix_int_consultas_tenant_tipo", "tenant_id", "tipo"),)

    config_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("int_provedor_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    tipo: Mapped[IntegracaoConsultaTipo] = mapped_column(
        _str_enum(IntegracaoConsultaTipo, "int_consulta_tipo", 20),
        nullable=False,
    )
    referencia_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    request_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[IntegracaoConsultaStatus] = mapped_column(
        _str_enum(IntegracaoConsultaStatus, "int_consulta_status", 10),
        nullable=False,
        default=IntegracaoConsultaStatus.SUCESSO,
    )
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntApiKey(TenantBaseModel):
    """Chave de API pública para consumidores externos (§12.5)."""

    __tablename__ = "int_api_keys"
    __table_args__ = (Index("ix_int_api_keys_prefix", "key_prefix"),)

    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    rate_limit_por_minuto: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_uso_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class IntOutboundWebhook(TenantBaseModel):
    """Endpoint de webhook outbound para eventos da API pública (§12.5)."""

    __tablename__ = "int_outbound_webhooks"
    __table_args__ = (Index("ix_int_outbound_tenant", "tenant_id"),)

    filial_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    eventos_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    secret_cripto: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    ultimo_disparo_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultimo_erro: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntSiteSlide(TenantBaseModel):
    """Slide do carrossel hero do site institucional (upload no ERP)."""

    __tablename__ = "int_site_slides"
    __table_args__ = (Index("ix_int_site_slides_tenant_ordem", "tenant_id", "sort_order"),)

    titulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="image/jpeg")
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
