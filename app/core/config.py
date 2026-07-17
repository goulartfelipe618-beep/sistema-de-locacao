"""Configurações da aplicação.

Todas as configurações são carregadas de variáveis de ambiente (arquivo ``.env``
em desenvolvimento) e validadas por Pydantic. O objeto :data:`settings` é um
singleton cacheado, seguro para importar em qualquer parte do código.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]


class Settings(BaseSettings):
    """Configurações tipadas e validadas da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ App
    app_name: str = "ERP Locadora"
    environment: Environment = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = False
    timezone: str = "America/Sao_Paulo"

    # ------------------------------------------------------------- Segurança
    secret_key: str = Field(min_length=32)
    session_cookie_name: str = "erp_session"
    session_max_age_seconds: int = 43_200
    session_https_only: bool = False
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    # CIDRs/IPs do proxy reverso permitidos para X-Forwarded-* (vazio = localhost).
    trusted_proxy_ips: str = "127.0.0.1,::1"

    # ----------------------------------------------------------- PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "erp"
    postgres_user: str = "erp_app"
    postgres_password: str = "erp_app"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ----------------------------------------------------------- Supabase (opcional)
    supabase_project_ref: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    # Connection string Postgres (Settings → Database → URI). Quando definida, substitui POSTGRES_*.
    supabase_db_url: str = ""

    # ---------------------------------------------------------------- Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # --------------------------------------------------------------- Celery
    celery_broker_db: int = 1
    celery_result_db: int = 2

    # ----------------------------------------------------------- Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "erp-locadora"
    r2_endpoint_url: str = ""
    r2_public_base_url: str = ""
    r2_presign_expire_seconds: int = 900

    # ------------------------------------------------------ Multiempresa/SaaS
    default_tenant_slug: str = "matriz"
    enforce_rls: bool = True

    # --------------------------------------------------- Auditoria / Retenção
    audit_retention_days: int = 730
    log_retention_days: int = 90

    # ------------------------------------------------------------------ CORS
    cors_origins: str = ""

    # ----------------------------------------------------------- Notificações
    notification_email_provider: Literal["simulador", "smtp"] = "simulador"
    notification_sms_provider: Literal["simulador", "http"] = "simulador"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # ----------------------------------------------------------- Validadores
    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level inválido: {value}. Use um de {sorted(allowed)}.")
        return upper

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: str) -> str:
        insecure_markers = (
            "CHANGE_ME",
            "change-in-production",
            "dev-secret-key",
            "test-secret-key",
        )
        lowered = value.lower()
        for marker in insecure_markers:
            if marker.lower() in lowered:
                # Aceito apenas fora de produção (validação cruzada no model_validator).
                break
        if len(value) < 32:
            raise ValueError("SECRET_KEY deve ter ao menos 32 caracteres.")
        return value

    def model_post_init(self, __context: object) -> None:
        """Validações cruzadas pós-carregamento (produção endurecida)."""
        insecure_markers = (
            "CHANGE_ME",
            "change-in-production",
            "dev-secret-key",
            "test-secret-key",
        )
        if self.environment == "production":
            if any(m.lower() in self.secret_key.lower() for m in insecure_markers):
                raise ValueError(
                    "SECRET_KEY insegura detectada em produção. "
                    "Gere com: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            if not self.session_https_only:
                raise ValueError("SESSION_HTTPS_ONLY deve ser true em produção.")
            if self.debug:
                raise ValueError("DEBUG deve ser false em produção.")

    # -------------------------------------------------- Propriedades derivadas
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """Indica se a aplicação está rodando em ambiente de produção."""
        return self.environment == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_async(self) -> str:
        """URL de conexão assíncrona (asyncpg) usada pela aplicação web/API."""
        if self.supabase_db_url:
            url = self.supabase_db_url
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if url.startswith("postgresql+psycopg://"):
                return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
            return url
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """URL de conexão síncrona (psycopg) usada por Alembic e utilitários."""
        if self.supabase_db_url:
            url = self.supabase_db_url
            if url.startswith("postgresql+asyncpg://"):
                return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    def _redis_url(self, db: int) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """URL do Redis para cache / sessões / locks."""
        return self._redis_url(self.redis_db)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_broker_url(self) -> str:
        """URL do broker Celery."""
        return self._redis_url(self.celery_broker_db)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_result_backend(self) -> str:
        """URL do backend de resultados Celery."""
        return self._redis_url(self.celery_result_db)

    @property
    def cors_origins_list(self) -> list[str]:
        """Lista de origens permitidas para CORS (API REST)."""
        if not self.cors_origins.strip():
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_proxy_ips_list(self) -> list[str]:
        """Lista de IPs/CIDRs confiáveis para cabeçalhos X-Forwarded-*."""
        if not self.trusted_proxy_ips.strip():
            return ["127.0.0.1", "::1"]
        return [item.strip() for item in self.trusted_proxy_ips.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância única e cacheada das configurações."""
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
