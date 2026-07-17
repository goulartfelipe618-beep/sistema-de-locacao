"""Serviços do módulo de Empresas/Filiais (regras de negócio)."""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_secret
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams
from app.core.storage import storage_service
from app.modules.audit.service import audit_service
from app.modules.tenants.branding import (
    branding_session_payload,
    encrypt_pfx,
    parse_pfx_metadata,
)
from app.modules.tenants.models import Filial, Tenant
from app.modules.tenants.repository import FilialRepository, TenantRepository
from app.modules.tenants.schemas import FilialCreate, FilialUpdate, TenantSystemUpdate, TenantUpdate
from app.modules.tenants.setup import can_complete_setup
from app.shared.enums import AuditAction

logger = get_logger(__name__)


class TenantService:
    """Regras de negócio para a empresa (tenant) do contexto."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tenants = TenantRepository(session)

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        """Retorna o tenant pelo ID ou levanta :class:`NotFoundError`."""
        tenant = await self.tenants.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Empresa não encontrada.")
        return tenant

    async def update_tenant(self, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant:
        """Atualiza dados cadastrais editáveis da empresa."""
        tenant = await self.get_tenant(tenant_id)
        payload = data.model_dump(exclude_unset=True)
        for field in ("legal_name", "trade_name", "email", "phone", "logo_storage_key", "logo_url"):
            if field in payload:
                value = payload[field]
                setattr(tenant, field, value.strip() if isinstance(value, str) and value else None)
        if "brand_primary_color" in payload:
            tenant.brand_primary_color = payload["brand_primary_color"]
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tenant",
            entity_id=tenant.id,
            description=f"Empresa atualizada: {tenant.legal_name}",
        )
        return tenant

    async def update_system_config(
        self,
        tenant_id: uuid.UUID,
        data: TenantSystemUpdate,
        *,
        complete_setup: bool = False,
    ) -> Tenant:
        """Atualiza configurações white label e contato da empresa."""
        tenant = await self.get_tenant(tenant_id)
        if data.cnpj != tenant.cnpj:
            existing = await self.tenants.get_by_cnpj(data.cnpj)
            if existing is not None and existing.id != tenant_id:
                raise ConflictError("CNPJ já cadastrado para outra empresa.", code="cnpj_taken")

        tenant.legal_name = data.legal_name.strip()
        tenant.trade_name = (data.trade_name or "").strip() or None
        tenant.app_display_name = data.app_display_name.strip()
        tenant.cnpj = data.cnpj
        tenant.email = data.email.strip()
        tenant.phone = data.phone
        tenant.ie = (data.ie or "").strip() or None
        tenant.website = (data.website or "").strip() or None
        tenant.document_footer_text = (data.document_footer_text or "").strip() or None
        tenant.brand_primary_color = data.brand_primary_color
        if data.logo_url is not None:
            tenant.logo_url = data.logo_url.strip() or None
        tenant.zip_code = data.zip_code
        tenant.address = data.address.strip()
        tenant.number = data.number.strip()
        tenant.complement = (data.complement or "").strip() or None
        tenant.district = (data.district or "").strip() or None
        tenant.city = data.city.strip()
        tenant.state = data.state

        if complete_setup:
            if not can_complete_setup(tenant):
                raise ValidationError(
                    "Preencha todos os campos obrigatórios e envie a logo antes de concluir."
                )
            tenant.setup_completed_at = datetime.now(tz=UTC)

        await audit_service.record(
            AuditAction.UPDATE,
            entity="tenant",
            entity_id=tenant.id,
            description="Configurações do sistema atualizadas",
        )
        return tenant

    async def upload_logo(
        self,
        tenant_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> Tenant:
        """Envia logo para R2 ou armazena inline (dev) e associa ao tenant."""
        if not file_bytes:
            raise ValidationError("Arquivo de logo vazio.")
        tenant = await self.get_tenant(tenant_id)
        safe_type = content_type or "image/png"
        if storage_service.is_configured():
            key = storage_service.build_key(tenant_id, "tenants", "logo", filename or "logo.png")
            storage_service.upload_bytes(key, file_bytes, safe_type)
            tenant.logo_storage_key = key
            tenant.logo_url = None
        else:
            encoded = base64.b64encode(file_bytes).decode("ascii")
            tenant.logo_url = f"data:{safe_type};base64,{encoded}"
            tenant.logo_storage_key = None
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tenant",
            entity_id=tenant.id,
            description="Logo da empresa atualizada",
        )
        return tenant

    async def update_certificate(
        self,
        tenant_id: uuid.UUID,
        *,
        pfx_bytes: bytes | None,
        password: str | None,
        remove: bool = False,
    ) -> Tenant:
        """Armazena ou remove certificado digital A1 (criptografado)."""
        tenant = await self.get_tenant(tenant_id)
        if remove:
            tenant.cert_a1_encrypted = None
            tenant.cert_a1_password_encrypted = None
            tenant.cert_a1_valid_until = None
            tenant.cert_a1_subject = None
            await audit_service.record(
                AuditAction.UPDATE,
                entity="tenant",
                entity_id=tenant.id,
                description="Certificado A1 removido",
            )
            return tenant
        if not pfx_bytes or not password:
            raise ValidationError("Arquivo PFX e senha são obrigatórios para o certificado.")
        try:
            meta = parse_pfx_metadata(pfx_bytes, password)
        except Exception as exc:
            raise ValidationError(f"Certificado inválido: {exc}") from exc
        tenant.cert_a1_encrypted = encrypt_pfx(pfx_bytes)
        tenant.cert_a1_password_encrypted = encrypt_secret(password)
        tenant.cert_a1_valid_until = meta.valid_until
        tenant.cert_a1_subject = meta.subject
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tenant",
            entity_id=tenant.id,
            description="Certificado A1 atualizado",
        )
        return tenant

    def session_branding(self, tenant: Tenant) -> dict:
        return branding_session_payload(tenant)


class FilialService:
    """Regras de negócio para filiais/unidades."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.filiais = FilialRepository(session)

    async def list_filiais(self, params: PageParams) -> Page[Filial]:
        """Lista filiais paginadas (ordenadas com a matriz primeiro)."""
        stmt = (
            self.filiais._base_query()
            .order_by(Filial.is_headquarters.desc(), Filial.name)
        )
        return await self.filiais.paginate(params, stmt=stmt)

    async def list_all(self) -> list[Filial]:
        """Lista todas as filiais ativas (para seletores)."""
        return await self.filiais.list_ordered()

    async def get_filial(self, filial_id: uuid.UUID) -> Filial:
        """Retorna a filial pelo ID ou levanta :class:`NotFoundError`."""
        filial = await self.filiais.get(filial_id)
        if filial is None:
            raise NotFoundError("Filial não encontrada.")
        return filial

    async def create_filial(self, data: FilialCreate, *, tenant_id: uuid.UUID) -> Filial:
        """Cria uma nova filial garantindo unicidade de código no tenant."""
        if await self.filiais.get_by_code(tenant_id, data.code):
            raise ConflictError("Já existe uma filial com este código.", code="code_taken")

        if data.is_headquarters:
            await self.filiais.clear_headquarters(tenant_id)

        filial = Filial(tenant_id=tenant_id, **data.model_dump())
        self.filiais.add(filial)
        await self.filiais.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="filial",
            entity_id=filial.id,
            description=f"Filial criada: {filial.code} - {filial.name}",
        )
        return filial

    async def update_filial(self, filial_id: uuid.UUID, data: FilialUpdate) -> Filial:
        """Atualiza uma filial existente."""
        filial = await self.get_filial(filial_id)
        payload = data.model_dump(exclude_unset=True)

        if payload.get("is_headquarters"):
            await self.filiais.clear_headquarters(filial.tenant_id)

        for field, value in payload.items():
            setattr(filial, field, value)

        await audit_service.record(
            AuditAction.UPDATE,
            entity="filial",
            entity_id=filial.id,
            description=f"Filial atualizada: {filial.code}",
        )
        return filial

    async def delete_filial(self, filial_id: uuid.UUID) -> None:
        """Aplica *soft delete* em uma filial."""
        filial = await self.get_filial(filial_id)
        await self.filiais.delete(filial)
        await audit_service.record(
            AuditAction.DELETE,
            entity="filial",
            entity_id=filial.id,
            description=f"Filial removida: {filial.code}",
        )
