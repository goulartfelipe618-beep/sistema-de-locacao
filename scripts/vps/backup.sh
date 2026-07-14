#!/usr/bin/env bash
# ==========================================================================
# Backup lógico do PostgreSQL (volume Docker) para ./backups/
# Uso: bash scripts/vps/backup.sh
# ==========================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

# shellcheck disable=SC1091
set -a
source .env
set +a

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${ROOT_DIR}/backups"
mkdir -p "${OUT_DIR}"
OUT_FILE="${OUT_DIR}/erp_${POSTGRES_DB:-erp}_${STAMP}.sql.gz"

echo "[backup] gerando ${OUT_FILE}..."
docker compose exec -T db \
  pg_dump -U "${POSTGRES_SUPERUSER:-postgres}" -d "${POSTGRES_DB:-erp}" \
  | gzip -c > "${OUT_FILE}"

echo "[backup] concluído: ${OUT_FILE}"
ls -lh "${OUT_FILE}"
