#!/usr/bin/env bash
# ==========================================================================
# Entrypoint da aplicação (VPS / Docker).
# Papéis: web | worker | beat | migrate | seed
# ==========================================================================
set -euo pipefail

ROLE="${1:-web}"

wait_for_db() {
  echo "[entrypoint] Aguardando PostgreSQL em ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  python - <<'PY'
import os
import socket
import sys
import time

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
last_err = "desconhecido"
for attempt in range(90):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("[entrypoint] PostgreSQL disponível.")
            sys.exit(0)
    except OSError as exc:
        last_err = str(exc)
        time.sleep(1)
try:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    resolved = ", ".join(sorted({i[4][0] for i in infos}))
except OSError as exc:
    resolved = f"DNS falhou: {exc}"
print(
    f"[entrypoint] Timeout aguardando PostgreSQL ({host}:{port}). "
    f"resolvido={resolved} ultimo_erro={last_err}",
    file=sys.stderr,
)
sys.exit(1)
PY
}

wait_for_redis() {
  echo "[entrypoint] Aguardando Redis em ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}..."
  python - <<'PY'
import os
import socket
import sys
import time

host = os.getenv("REDIS_HOST", "redis")
port = int(os.getenv("REDIS_PORT", "6379"))
for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("[entrypoint] Redis disponível.")
            sys.exit(0)
    except OSError:
        time.sleep(1)
print("[entrypoint] Timeout aguardando Redis.", file=sys.stderr)
sys.exit(1)
PY
}

case "${ROLE}" in
  web)
    wait_for_db
    wait_for_redis
    WORKERS="${WEB_CONCURRENCY:-2}"
    TRUSTED="${TRUSTED_PROXY_IPS:-nginx}"
    echo "[entrypoint] Iniciando web (gunicorn + uvicorn) workers=${WORKERS}"
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --workers "${WORKERS}" \
      --timeout 120 \
      --graceful-timeout 30 \
      --access-logfile - \
      --error-logfile - \
      --forwarded-allow-ips "${TRUSTED}"
    ;;
  worker)
    wait_for_db
    wait_for_redis
    exec celery -A app.workers.celery_app.celery_app worker \
      --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
      --concurrency="${CELERY_CONCURRENCY:-4}"
    ;;
  beat)
    wait_for_db
    wait_for_redis
    exec celery -A app.workers.celery_app.celery_app beat \
      --loglevel="${CELERY_LOG_LEVEL:-INFO}"
    ;;
  migrate)
    wait_for_db
    echo "[entrypoint] Aplicando migrations Alembic..."
    exec alembic upgrade head
    ;;
  seed)
    wait_for_db
    echo "[entrypoint] Executando seed idempotente..."
    exec python -m scripts.seed
    ;;
  *)
    exec "$@"
    ;;
esac
