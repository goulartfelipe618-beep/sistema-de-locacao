"""Divide o SQL gerado pelo Alembic em arquivos por revisão (Supabase MCP / db push)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "supabase" / "migrations" / "_full_upgrade.sql"
OUT_DIR = ROOT / "supabase" / "migrations" / "split"

MARKER = re.compile(r"^-- Running upgrade\s+(.*?)\s+->\s+(\S+)", re.MULTILINE)


def _slug(rev: str, title: str | None) -> str:
    base = rev.replace(" ", "_").lower()
    if title:
        part = re.sub(r"[^a-z0-9_]+", "_", title.strip().lower()).strip("_")
        if part:
            return f"{base}_{part}"
    return base


def split_migrations() -> list[Path]:
    if not SOURCE.is_file():
        raise SystemExit(f"Arquivo não encontrado: {SOURCE}. Rode: python -m alembic upgrade head --sql")

    text = SOURCE.read_text(encoding="utf-8")
    # Remove envelope transaction do Alembic offline (aplicamos por migration).
    text = text.removeprefix("BEGIN;\n\n")
    if text.rstrip().endswith("COMMIT;"):
        text = text.rstrip()[:- len("COMMIT;")].rstrip()

    matches = list(MARKER.finditer(text))
    if not matches:
        raise SystemExit("Nenhum marcador '-- Running upgrade' encontrado.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if not block:
            continue

        to_rev = match.group(2).strip()
        _from = match.group(1).strip()
        slug = _slug(to_rev, None)

        # Garante extensões usadas pelo ERP
        prelude = "CREATE EXTENSION IF NOT EXISTS pgcrypto;\n\n"
        sql = prelude + block + "\n"

        path = OUT_DIR / f"{slug}.sql"
        path.write_text(sql, encoding="utf-8")
        written.append(path)

    # Bootstrap alembic_version table
    bootstrap = OUT_DIR / "0000_bootstrap_alembic_version.sql"
    if not bootstrap.exists():
        bootstrap.write_text(
            "CREATE EXTENSION IF NOT EXISTS pgcrypto;\n\n"
            "CREATE TABLE IF NOT EXISTS alembic_version (\n"
            "    version_num VARCHAR(32) NOT NULL,\n"
            "    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)\n"
            ");\n",
            encoding="utf-8",
        )
        written.insert(0, bootstrap)

    return written


def main() -> None:
    files = split_migrations()
    print(f"Gerados {len(files)} arquivo(s) em {OUT_DIR.relative_to(ROOT)}")
    for p in files:
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
