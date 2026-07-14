#!/usr/bin/env bash
# ==========================================================================
# Restaura um dump gerado por scripts/vps/backup.sh
# Uso: bash scripts/vps/restore.sh backups/erp_erp_YYYYMMDDTHHMMSSZ.sql.gz
# ATENÇÃO: sobrescreve o banco atual.
# ==========================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

DUMP_FILE="${1:-}"
if [[ -z "${DUMP_FILE}" || ! -f "${DUMP_FILE}" ]]; then
  echo "Uso: bash scripts/vps/restore.sh <arquivo.sql.gz>"
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

echo "[restore] ATENÇÃO: isso sobrescreve o banco ${POSTGRES_DB:-erp}."
read -r -p "Digite 'RESTORE' para confirmar: " CONFIRM
if [[ "${CONFIRM}" != "RESTORE" ]]; then
  echo "Cancelado."
  exit 1
fi

echo "[restore] restaurando ${DUMP_FILE}..."
gunzip -c "${DUMP_FILE}" \
  | docker compose exec -T db \
      psql -U "${POSTGRES_SUPERUSER:-postgres}" -d "${POSTGRES_DB:-erp}"

echo "[restore] concluído. Reinicie a aplicação: docker compose up -d"
