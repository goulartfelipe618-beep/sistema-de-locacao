#!/usr/bin/env bash
# ==========================================================================
# Prepara uma VPS Ubuntu 24.04 LTS com Docker Engine + Compose Plugin + Git.
# Uso (como root ou com sudo):
#   curl -fsSL ... | bash
#   OU: sudo bash scripts/vps/setup-ubuntu.sh
# ==========================================================================
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root: sudo bash scripts/vps/setup-ubuntu.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl git gnupg ufw

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

. /etc/os-release
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable || true

echo
echo "Docker instalado:"
docker --version
docker compose version
echo
echo "Próximos passos:"
echo "  1) git clone <seu-repositorio> /opt/erp-locadora"
echo "  2) cd /opt/erp-locadora && cp .env.example .env && nano .env"
echo "  3) docker compose up -d --build"
