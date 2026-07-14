#!/usr/bin/env bash
# ==========================================================================
# Inicialização do PostgreSQL (primeiro boot do volume).
# Cria o role de aplicação NOSUPERUSER (obrigatório para RLS efetivo).
# Variáveis injetadas pelo docker-compose: APP_DB_USER / APP_DB_PASSWORD / APP_DB_NAME
# ==========================================================================
set -euo pipefail

APP_DB_USER="${APP_DB_USER:-erp_app}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:?APP_DB_PASSWORD não definido}"
APP_DB_NAME="${APP_DB_NAME:-erp}"

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<-EOSQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${APP_DB_USER}') THEN
      CREATE ROLE ${APP_DB_USER} LOGIN PASSWORD '${APP_DB_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
   ELSE
      ALTER ROLE ${APP_DB_USER} WITH LOGIN PASSWORD '${APP_DB_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
   END IF;
END
\$\$;

GRANT CONNECT ON DATABASE ${APP_DB_NAME} TO ${APP_DB_USER};
EOSQL

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${APP_DB_NAME}" <<-EOSQL
ALTER SCHEMA public OWNER TO ${APP_DB_USER};
GRANT ALL ON SCHEMA public TO ${APP_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${APP_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${APP_DB_USER};
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "unaccent";
EOSQL

echo "[postgres-init] Role ${APP_DB_USER} pronto (NOSUPERUSER / RLS)."
