"""Configuração do BFF do site (white-label — um deploy por locadora)."""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BFF_DIR = Path(__file__).resolve().parent
_SITE_DIR = _BFF_DIR.parent
_REPO_ROOT = _SITE_DIR.parent
_ENV_CANDIDATES = [
    _REPO_ROOT / ".env",
    _SITE_DIR / ".env",
    _BFF_DIR / ".env",
]
_ENV_FILES = [str(p) for p in _ENV_CANDIDATES if p.is_file()] or [".env"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ERP — preferir rede interna (Docker/Easypanel): http://web:8000 ou http://erp-locadora:8000
    erp_internal_url: str = ""
    erp_base_url: str = "http://web:8000"
    erp_api_key: str = ""
    erp_api_key_catalogo: str = ""
    erp_api_key_disponibilidade: str = ""
    erp_api_key_veiculos: str = ""
    erp_api_key_pricing: str = ""
    erp_api_key_reservas: str = ""
    erp_tenant_slug: str = Field(
        default="matriz",
        validation_alias=AliasChoices("ERP_TENANT_SLUG", "DEFAULT_TENANT_SLUG"),
    )

    site_public_url: str = "http://localhost:8080"
    site_allowed_origins: str = "http://localhost:8080,http://127.0.0.1:8080"

    bff_host: str = "0.0.0.0"
    bff_port: int = 8090
    bff_request_timeout_seconds: float = 20.0

    def api_key_for_scope(self, scope: str) -> str:
        by_scope = {
            "catalogo:read": self.erp_api_key_catalogo,
            "disponibilidade:read": self.erp_api_key_disponibilidade,
            "veiculos:read": self.erp_api_key_veiculos,
            "pricing:read": self.erp_api_key_pricing,
            "reservas:write": self.erp_api_key_reservas,
        }
        return (by_scope.get(scope) or self.erp_api_key).strip()

    @property
    def erp_api_base(self) -> str:
        internal = self.erp_internal_url.strip()
        if internal:
            return internal.rstrip("/")
        return self.erp_base_url.rstrip("/")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.site_allowed_origins.split(",") if o.strip()]


settings = Settings()
