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
    erp_internal_url: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_INTERNAL_URL"),
    )
    erp_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_BASE_URL"),
    )
    erp_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_API_KEY", "SITE_ERP_API_KEY"),
    )
    erp_api_key_catalogo: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_API_KEY_CATALOGO"),
    )
    erp_api_key_disponibilidade: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_API_KEY_DISPONIBILIDADE"),
    )
    erp_api_key_veiculos: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_API_KEY_VEICULOS"),
    )
    erp_api_key_pricing: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_API_KEY_PRICING"),
    )
    erp_api_key_reservas: str = Field(
        default="",
        validation_alias=AliasChoices("ERP_API_KEY_RESERVAS"),
    )
    site_atendimento_webhook_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SITE_ATENDIMENTO_WEBHOOK_URL",
            "SITE_CHAT_WEBHOOK_URL",
        ),
    )
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
        public = self.erp_base_url.strip()
        if public:
            return public.rstrip("/")
        # Fallback Compose (site + erp no mesmo stack)
        return "http://web:8000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.site_allowed_origins.split(",") if o.strip()]

    @property
    def config_issues(self) -> list[str]:
        issues: list[str] = []
        if not self.api_key_for_scope("catalogo:read"):
            issues.append("ERP_API_KEY ou ERP_API_KEY_CATALOGO ausente")
        slug = self.erp_tenant_slug.strip().lower()
        if slug == "rodavia":
            issues.append(
                "ERP_TENANT_SLUG=rodavia não existe no ERP; use matriz (DEFAULT_TENANT_SLUG)"
            )
        if not self.erp_internal_url.strip() and not self.erp_base_url.strip():
            issues.append(
                "Defina ERP_INTERNAL_URL (Docker/Easypanel) ou ERP_BASE_URL (dev local → ERP remoto)"
            )
        if not self.site_atendimento_webhook_url.strip():
            issues.append(
                "SITE_ATENDIMENTO_WEBHOOK_URL ausente (Integrações → API Pública no ERP)"
            )
        return issues


settings = Settings()
