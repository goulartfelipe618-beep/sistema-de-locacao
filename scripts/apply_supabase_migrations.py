"""Aplica migrations SQL splitadas no Postgres (Supabase ou local).

Uso:
  1. Defina SUPABASE_DB_URL no .env (Settings → Database → Connection string → URI)
  2. python scripts/apply_supabase_migrations.py

Alternativa: autentique o MCP Supabase no Cursor e peça apply_migration por revisão.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT_DIR = ROOT / "supabase" / "migrations" / "split"


def main() -> None:
    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        try:
            from app.core.config import settings

            db_url = settings.supabase_db_url
        except Exception:
            db_url = ""
    if not db_url:
        print(
            "Defina SUPABASE_DB_URL no .env (connection string Postgres do Supabase).\n"
            "Ex.: postgresql://postgres.[ref]:[SENHA]@aws-0-[regiao].pooler.supabase.com:6543/postgres",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Instale psycopg: pip install psycopg[binary]") from exc

    files = sorted(SPLIT_DIR.glob("*.sql"))
    if not files:
        raise SystemExit(f"Nenhum SQL em {SPLIT_DIR}. Rode scripts/split_alembic_supabase.py")

    print(f"Conectando e aplicando {len(files)} migration(s)...")
    with psycopg.connect(db_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            for path in files:
                sql = path.read_text(encoding="utf-8")
                print(f"  → {path.name}")
                cur.execute(sql)
            conn.commit()
    print("Migrations aplicadas com sucesso.")


if __name__ == "__main__":
    main()
