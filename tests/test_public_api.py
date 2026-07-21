"""Rotas e schemas da API pública (site)."""

from __future__ import annotations


def test_public_api_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/v1/public/empresa" in paths
    assert "/api/v1/public/filiais" in paths
    assert "/api/v1/public/grupos" in paths
    assert "/api/v1/public/cotacao" in paths
    assert "/api/v1/public/reservas/site" in paths
    assert "/api/v1/public/ping" in paths


def test_public_scopes_include_catalogo_and_pricing() -> None:
    from app.modules.integracoes.web import API_PUBLIC_SCOPES

    codes = {s[0] for s in API_PUBLIC_SCOPES}
    assert "catalogo:read" in codes
    assert "pricing:read" in codes


def test_public_reserva_site_schema() -> None:
    from app.modules.integracoes.public_schemas import PublicReservaSiteCreate

    assert "cliente" in PublicReservaSiteCreate.model_fields
