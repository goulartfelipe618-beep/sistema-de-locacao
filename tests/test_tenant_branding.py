"""Testes de branding e certificado A1 (§14.1)."""

from __future__ import annotations

from datetime import date

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.tenants.branding import (
    branding_pdf_context,
    branding_session_payload,
    encrypt_pfx,
    decrypt_pfx,
)
from app.modules.tenants.models import Tenant
from app.shared.enums import TenantStatus


def _tenant(**kwargs) -> Tenant:
    base = dict(
        slug="demo",
        legal_name="Locadora Demo LTDA",
        trade_name="Demo Locações",
        app_display_name="Demo ERP",
        cnpj="12345678000199",
        status=TenantStatus.ACTIVE,
        plan="standard",
        email="contato@demo.com",
        phone="11999999999",
        brand_primary_color="#2563eb",
        logo_url="https://example.com/logo.png",
    )
    base.update(kwargs)
    return Tenant(**base)


def test_permissoes_empresa_editar_registrada() -> None:
    assert "configuracoes.empresa.editar" in PERMISSIONS_BY_CODE


def test_branding_session_payload() -> None:
    payload = branding_session_payload(_tenant())
    assert payload["display_name"] == "Demo ERP"
    assert payload["brand_primary_color"] == "#2563eb"
    assert payload["logo_url"] == "https://example.com/logo.png"
    assert payload["has_logo"] is True
    assert payload["setup_complete"] is False


def test_branding_session_payload_omits_presigned_logo_url() -> None:
    payload = branding_session_payload(_tenant(logo_url=None, logo_storage_key="tenants/x/logo.png"), include_logo_url=False)
    assert payload["logo_url"] is None
    assert payload["has_logo"] is True


def test_branding_session_payload_app_display_name_priority() -> None:
    payload = branding_session_payload(_tenant(app_display_name="Minha Marca"))
    assert payload["display_name"] == "Minha Marca"


def test_branding_pdf_context() -> None:
    ctx = branding_pdf_context(_tenant(cert_a1_encrypted="x", cert_a1_valid_until=date(2027, 1, 1)))
    assert ctx["brand_primary_color"] == "#2563eb"
    assert ctx["cert_configured"] is True
    assert ctx["cert_valid_until"] == date(2027, 1, 1)


def test_pfx_encrypt_roundtrip() -> None:
    raw = b"fake-pfx-content"
    enc = encrypt_pfx(raw)
    assert decrypt_pfx(enc) == raw


def test_tenant_cert_configured_property() -> None:
    assert _tenant().cert_configured is False
    assert _tenant(cert_a1_encrypted="enc").cert_configured is True
