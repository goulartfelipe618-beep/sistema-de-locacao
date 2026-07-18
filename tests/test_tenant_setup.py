"""Testes de onboarding e white label (configurações do sistema)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.tenants.models import Tenant
from app.modules.tenants.setup import (
    format_tenant_address,
    is_setup_complete,
    is_setup_exempt_path,
    post_login_redirect_url,
    resolve_setup_redirect,
    setup_missing_fields,
    sync_tenant_session_flags,
)
from app.shared.enums import TenantStatus


def _tenant(**kwargs) -> Tenant:
    base = dict(
        slug="demo",
        legal_name="Locadora Demo LTDA",
        trade_name="Demo Locações",
        app_display_name="Demo ERP",
        cnpj="11222333000181",
        status=TenantStatus.ACTIVE,
        plan="standard",
        email="contato@demo.com",
        phone="11999999999",
        brand_primary_color="#2563eb",
        logo_url="https://example.com/logo.png",
        zip_code="01310100",
        address="Av. Paulista",
        number="1000",
        city="São Paulo",
        state="SP",
    )
    base.update(kwargs)
    return Tenant(**base)


def test_setup_incomplete_lists_missing_fields() -> None:
    tenant = _tenant(
        cnpj=None,
        email=None,
        logo_url=None,
        logo_storage_key=None,
        setup_completed_at=None,
    )
    missing = setup_missing_fields(tenant)
    assert "CNPJ" in missing
    assert "E-mail" in missing
    assert "Logo" in missing


def test_setup_complete_when_timestamp_set() -> None:
    tenant = _tenant(setup_completed_at=datetime.now(tz=UTC))
    assert is_setup_complete(tenant) is True
    assert setup_missing_fields(tenant) == []


def test_setup_exempt_paths() -> None:
    assert is_setup_exempt_path("/login") is True
    assert is_setup_exempt_path("/configuracoes/sistema/editar") is True
    assert is_setup_exempt_path("/referencia/ibge/ufs") is True
    assert is_setup_exempt_path("/referencia/ibge/municipios/SP") is True
    assert is_setup_exempt_path("/cadastros/cep/01310100") is True
    assert is_setup_exempt_path("/") is False
    assert is_setup_exempt_path("/cadastros/clientes") is False


def test_resolve_setup_redirect_admin() -> None:
    session = {"tenant_setup_complete": False, "can_edit_empresa": True}
    assert resolve_setup_redirect(session) == "/configuracoes/sistema"


def test_resolve_setup_redirect_operator() -> None:
    session = {"tenant_setup_complete": False, "can_edit_empresa": False}
    assert resolve_setup_redirect(session) == "/configuracoes/sistema/aguardando"


def test_post_login_redirect_when_complete() -> None:
    session = {"tenant_setup_complete": True}
    assert post_login_redirect_url(session) == "/"


def test_sync_tenant_session_flags() -> None:
    tenant = _tenant(setup_completed_at=datetime.now(tz=UTC))
    session: dict = {}
    sync_tenant_session_flags(session, tenant, can_edit_empresa=True)
    assert session["tenant_setup_complete"] is True
    assert session["can_edit_empresa"] is True
    assert session["tenant_branding"]["display_name"] == "Demo ERP"
    assert session["tenant_branding"]["setup_complete"] is True


def test_format_tenant_address() -> None:
    text = format_tenant_address(_tenant())
    assert "Av. Paulista" in text
    assert "São Paulo" in text
    assert "CEP" in text
