#!/usr/bin/env bash
# ==========================================================================
# Deploy / atualização na VPS:
#   cd /opt/erp-locadora && bash scripts/vps/deploy.sh
# Equivalente a: git pull && docker compose up -d --build
# ==========================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f .env ]]; then
  echo "Arquivo .env não encontrado. Execute: cp .env.example .env && nano .env"
  exit 1
fi

echo "[deploy] git pull..."
git pull --ff-only

echo "[deploy] docker compose up -d --build..."
docker compose up -d --build

echo "[deploy] status:"
docker compose ps

echo "[deploy] pronto."
