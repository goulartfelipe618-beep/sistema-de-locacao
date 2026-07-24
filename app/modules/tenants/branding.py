"""Branding e certificado digital da empresa (§14.1)."""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.storage import storage_service
from app.modules.tenants.models import Tenant


@dataclass(slots=True)
class CertMetadata:
    subject: str
    valid_until: date


def resolve_logo_url(tenant: Tenant) -> str | None:
    """URL exibível da logo (externa ou presign R2)."""
    if tenant.logo_url:
        return tenant.logo_url
    if tenant.logo_storage_key and storage_service.is_configured():
        try:
            return storage_service.generate_presigned_download(tenant.logo_storage_key)
        except Exception:
            return None
    return None


def branding_session_payload(tenant: Tenant, *, include_logo_url: bool = True) -> dict[str, Any]:
    """Resumo leve para sessão/UI (sidebar, CSS)."""
    logo = resolve_logo_url(tenant) if include_logo_url else None
    return {
        "display_name": tenant.sidebar_display_name,
        "brand_primary_color": tenant.brand_primary_color or "#1e5a8a",
        "logo_url": logo,
        "has_logo": tenant.has_logo,
        "setup_complete": tenant.setup_complete,
        "fiscal_emissao_habilitada": bool(tenant.fiscal_emissao_habilitada),
    }


def branding_pdf_context(tenant: Tenant) -> dict[str, Any]:
    """Campos extras para templates PDF."""
    from app.modules.tenants.setup import format_tenant_address

    color = tenant.brand_primary_color or "#1e5a8a"
    return {
        "empresa_logo_url": resolve_logo_url(tenant),
        "brand_primary_color": color,
        "empresa_display_name": tenant.sidebar_display_name,
        "empresa_endereco": format_tenant_address(tenant),
        "empresa_ie": tenant.ie or "—",
        "empresa_website": tenant.website or "—",
        "document_footer_text": tenant.document_footer_text,
        "cert_configured": bool(tenant.cert_a1_encrypted),
        "cert_valid_until": tenant.cert_a1_valid_until,
        "cert_subject": tenant.cert_a1_subject,
        "fiscal_emissao_habilitada": bool(tenant.fiscal_emissao_habilitada),
    }


def parse_pfx_metadata(pfx_bytes: bytes, password: str) -> CertMetadata:
    """Extrai titular e validade de certificado A1 (.pfx)."""
    from cryptography.hazmat.primitives.serialization import pkcs12

    _, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, password.encode())
    if cert is None:
        raise ValueError("Arquivo PFX sem certificado.")
    subject = cert.subject.rfc4514_string()
    valid_until = cert.not_valid_after_utc.date()
    return CertMetadata(subject=subject[:255], valid_until=valid_until)


def encrypt_pfx(pfx_bytes: bytes) -> str:
    encoded = base64.b64encode(pfx_bytes).decode()
    return encrypt_secret(encoded)


def decrypt_pfx(encrypted: str) -> bytes:
    decoded = decrypt_secret(encrypted)
    return base64.b64decode(decoded)


def get_cert_bundle(tenant: Tenant) -> tuple[bytes, str] | None:
    """Retorna (pfx_bytes, senha) descriptografados ou None."""
    if not tenant.cert_a1_encrypted or not tenant.cert_a1_password_encrypted:
        return None
    try:
        pfx = decrypt_pfx(tenant.cert_a1_encrypted)
        password = decrypt_secret(tenant.cert_a1_password_encrypted)
        return pfx, password
    except ValueError:
        return None
