"""Testes de integração Supabase (config e migrations exportadas)."""

from __future__ import annotations

from pathlib import Path


def test_supabase_mcp_config_exists() -> None:
    mcp = Path(".cursor/mcp.json").read_text(encoding="utf-8")
    assert "mcp.supabase.com/mcp" in mcp
    assert "tchbfavyhhnuhpssqnih" in mcp
    assert "features=database" in mcp


def test_supabase_split_migrations_complete() -> None:
    split = Path("supabase/migrations/split")
    files = sorted(split.glob("*.sql"))
    assert len(files) >= 23
    names = {p.name for p in files}
    assert "0001_foundation.sql" in names
    assert "0022_remove_whatsapp_redes.sql" in names
    assert "0023_intermediacao.sql" in names


def test_config_supabase_db_url_override() -> None:
    from app.core.config import Settings

    s = Settings(
        supabase_db_url="postgresql://postgres:secret@db.example.com:5432/postgres",
        secret_key="x" * 64,
        environment="development",
    )
    assert "postgresql+psycopg://" in s.database_url_sync
    assert "postgresql+asyncpg://" in s.database_url_async
