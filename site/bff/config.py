"""Configuração do BFF do site (domínio e ERP via variáveis de ambiente)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ERP (Easypanel hoje; URL fixa interna)
    erp_base_url: str = "https://loca-erp-locadora.eal7ix.easypanel.host"
    erp_api_key: str = ""
    erp_tenant_slug: str = "rodavia"

    # Site público — altere quando trocar o domínio (CORS + links absolutos opcionais)
    site_public_url: str = "http://localhost:8080"
    site_allowed_origins: str = "http://localhost:8080,http://127.0.0.1:8080"

    bff_host: str = "0.0.0.0"
    bff_port: int = 8090
    bff_request_timeout_seconds: float = 20.0

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.site_allowed_origins.split(",") if o.strip()]


settings = Settings()
