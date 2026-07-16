"""Factory de provedores fiscais (simulador vs certificado A1) (§10 + §14.1)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fiscal.adapters.certificado import CertBundle
from app.modules.fiscal.adapters.certificado_nfe import CertificadoSefaz
from app.modules.fiscal.adapters.certificado_nfse import CertificadoNfse
from app.modules.fiscal.adapters.nfe_port import SefazNfePort
from app.modules.fiscal.adapters.nfse_port import NfseProvedorPort
from app.modules.fiscal.adapters.simulador_nfe import SimuladorSefaz
from app.modules.fiscal.adapters.simulador_nfse import SimuladorNfse
from app.modules.tenants.branding import get_cert_bundle
from app.modules.tenants.repository import TenantRepository


async def _cert_bundle(session: AsyncSession, tenant_id: uuid.UUID) -> CertBundle | None:
    tenant = await TenantRepository(session).get(tenant_id)
    if tenant is None:
        return None
    bundle = get_cert_bundle(tenant)
    if bundle is None:
        return None
    pfx, password = bundle
    return CertBundle(
        pfx_bytes=pfx,
        password=password,
        subject=tenant.cert_a1_subject or "",
    )


async def get_nfe_provider(session: AsyncSession, tenant_id: uuid.UUID) -> SefazNfePort:
    """Resolve provedor NF-e: certificado A1 quando configurado, senão simulador."""
    cert = await _cert_bundle(session, tenant_id)
    if cert is not None:
        return CertificadoSefaz(cert)
    return SimuladorSefaz()


async def get_nfse_provider(session: AsyncSession, tenant_id: uuid.UUID) -> NfseProvedorPort:
    """Resolve provedor NFS-e: certificado A1 quando configurado, senão simulador."""
    cert = await _cert_bundle(session, tenant_id)
    if cert is not None:
        return CertificadoNfse(cert)
    return SimuladorNfse()
