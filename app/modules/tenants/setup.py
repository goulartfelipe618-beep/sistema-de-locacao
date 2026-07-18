"""Onboarding e validação das configurações do sistema (white label)."""

from __future__ import annotations

import uuid
from typing import Any

from starlette.requests import Request

from app.core.logging import get_logger
from app.modules.tenants.branding import branding_session_payload
from app.modules.tenants.models import Tenant

logger = get_logger(__name__)

SETUP_PATH = "/configuracoes/sistema"
SETUP_PENDING_PATH = "/configuracoes/sistema/aguardando"
SETUP_EDIT_PATH = "/configuracoes/sistema/editar"

SETUP_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/login",
    "/logout",
    "/static",
    "/api/",
    "/favicon.ico",
    "/configuracoes/sistema",
    "/configuracoes/tema",
    "/cadastros/ibge",
    "/cadastros/cep",
    "/referencia/",
    "/health",
)


def is_setup_complete(tenant: Tenant) -> bool:
    """Indica se o tenant concluiu o onboarding obrigatório."""
    return tenant.setup_completed_at is not None


def setup_missing_fields(tenant: Tenant) -> list[str]:
    """Lista campos obrigatórios ainda ausentes (para mensagens de UI)."""
    missing: list[str] = []
    if not (tenant.legal_name or "").strip():
        missing.append("Razão social")
    if not (tenant.app_display_name or tenant.trade_name or "").strip():
        missing.append("Nome exibido no sistema")
    if not tenant.cnpj:
        missing.append("CNPJ")
    if not tenant.email:
        missing.append("E-mail")
    if not tenant.phone:
        missing.append("Telefone")
    if not tenant.brand_primary_color:
        missing.append("Cor primária")
    if not tenant.has_logo:
        missing.append("Logo")
    if not tenant.zip_code:
        missing.append("CEP")
    if not tenant.address:
        missing.append("Endereço")
    if not tenant.number:
        missing.append("Número")
    if not tenant.city:
        missing.append("Cidade")
    if not tenant.state:
        missing.append("UF")
    return missing


def can_complete_setup(tenant: Tenant) -> bool:
    return not setup_missing_fields(tenant)


def is_setup_exempt_path(path: str) -> bool:
    if path == "/":
        return False
    return any(path == prefix or path.startswith(prefix) for prefix in SETUP_EXEMPT_PREFIXES)


def resolve_setup_redirect(session: dict[str, Any]) -> str | None:
    """Retorna URL de redirecionamento se o tenant ainda não concluiu setup."""
    if session.get("tenant_setup_complete", True):
        return None
    if session.get("can_edit_empresa"):
        return SETUP_PATH
    return SETUP_PENDING_PATH


def post_login_redirect_url(session: dict[str, Any]) -> str:
    redirect = resolve_setup_redirect(session)
    return redirect or "/"


def sync_tenant_session_flags(
    session: dict[str, Any],
    tenant: Tenant,
    *,
    can_edit_empresa: bool,
) -> None:
    """Atualiza flags de sessão usadas pelo middleware e pela sidebar."""
    session["tenant_branding"] = branding_session_payload(tenant)
    session["tenant_setup_complete"] = is_setup_complete(tenant)
    session["can_edit_empresa"] = can_edit_empresa


async def refresh_tenant_session_from_db(request: Request) -> None:
    """Sincroniza branding e status de setup da sessão com o banco (fonte da verdade)."""
    session = request.scope.get("session")
    if not isinstance(session, dict):
        return
    if not session.get("user_id") or not session.get("tenant_id"):
        return

    from app.core.database import _apply_tenant_context, _reset_tenant_context, async_session_factory
    from app.modules.tenants.repository import TenantRepository

    try:
        tenant_id = uuid.UUID(str(session["tenant_id"]))
    except (ValueError, TypeError):
        return

    db = async_session_factory()
    try:
        await _apply_tenant_context(db, tenant_id)
        tenant = await TenantRepository(db).get(tenant_id)
        if tenant is not None:
            sync_tenant_session_flags(
                session,
                tenant,
                can_edit_empresa=bool(session.get("can_edit_empresa")),
            )
    except Exception:
        logger.warning(
            "Falha ao sincronizar sessão do tenant com o banco.",
            exc_info=True,
        )
    finally:
        await _reset_tenant_context(db)
        await db.close()


def populate_authenticated_session(
    session: dict[str, Any],
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    filial_id: uuid.UUID | None,
    is_superuser: bool,
    tenant: Tenant,
    permission_codes: set[str],
) -> None:
    """Preenche a sessão web após login bem-sucedido."""
    can_edit = is_superuser or "configuracoes.empresa.editar" in permission_codes
    session["user_id"] = str(user_id)
    session["tenant_id"] = str(tenant_id)
    session["filial_id"] = str(filial_id) if filial_id else None
    session["is_superuser"] = is_superuser
    sync_tenant_session_flags(session, tenant, can_edit_empresa=can_edit)


def format_tenant_address(tenant: Tenant) -> str:
    """Endereço formatado para PDFs e telas."""
    parts: list[str] = []
    line = tenant.address or ""
    if tenant.number:
        line = f"{line}, {tenant.number}" if line else tenant.number
    if line:
        parts.append(line)
    if tenant.complement:
        parts.append(tenant.complement)
    if tenant.district:
        parts.append(tenant.district)
    city_state = " — ".join(p for p in (tenant.city, tenant.state) if p)
    if city_state:
        parts.append(city_state)
    if tenant.zip_code:
        parts.append(f"CEP {tenant.zip_code[:5]}-{tenant.zip_code[5:]}" if len(tenant.zip_code) == 8 else f"CEP {tenant.zip_code}")
    return " · ".join(parts) if parts else "—"
