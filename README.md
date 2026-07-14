# ERP de Locação de Veículos — Sistema Administrativo

ERP SaaS multiempresa para locadoras de veículos (**Fase 0 — Fundação**).

**Ambiente suportado: exclusivamente VPS Linux (Ubuntu 24.04 LTS) com Docker Engine.**

Não há suporte a execução local no Windows, Docker Desktop, WSL ou Hyper-V.

---

## Fluxo de trabalho

```
Cursor  →  git commit / push  →  GitHub  →  VPS (git pull)  →  docker compose up -d --build
```

Na VPS, após o `.env` configurado uma única vez:

```bash
git pull
docker compose up -d --build
```

Isso reconstrói a imagem, aplica migrations, executa o seed idempotente e sobe
`db`, `redis`, `web`, `worker`, `beat` e `nginx`.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API / Web | FastAPI + Gunicorn (Uvicorn workers) |
| Templates | Jinja2 + HTMX + Alpine.js |
| ORM / Migrations | SQLAlchemy 2.0 (async) + Alembic |
| Banco | PostgreSQL 16 (Row-Level Security) |
| Cache / Broker | Redis 7 |
| Background | Celery + Celery Beat |
| Arquivos | Cloudflare R2 |
| Proxy | Nginx |
| Runtime | Docker Engine + Docker Compose Plugin |

---

## Instalação da VPS (Ubuntu 24.04 LTS)

### 1) Preparar o servidor

```bash
sudo bash scripts/vps/setup-ubuntu.sh
```

O script instala Docker Engine, Compose Plugin, Git e abre as portas 22/80/443 no UFW.

### 2) Clonar o repositório

```bash
sudo mkdir -p /opt
sudo git clone git@github.com:SEU_ORG/erp-locadora.git /opt/erp-locadora
# ou: https://github.com/SEU_ORG/erp-locadora.git
cd /opt/erp-locadora
```

### 3) Configurar o `.env`

```bash
cp .env.example .env
nano .env
```

Preencha **obrigatoriamente**:

- `SECRET_KEY` (forte, gerado com `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`)
- `POSTGRES_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`
- `SESSION_HTTPS_ONLY=true` (produção com TLS no front — Cloudflare/Certbot)

> Sem TLS ainda? Use temporariamente `ENVIRONMENT=staging` e `SESSION_HTTPS_ONLY=false`
> até terminar o certificado. Em `production`, cookies seguros são obrigatórios.

### 4) Primeiro deploy

```bash
docker compose up -d --build
```

Aguarde os healthchecks:

```bash
docker compose ps
docker compose logs -f --tail=100
```

Acesse: `http://SEU_IP/` (Nginx → app).  
API docs: `http://SEU_IP/api/docs`

Login inicial: valores definidos em `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`.

---

## Atualização via Git (dia a dia)

No diretório do projeto na VPS:

```bash
git pull
docker compose up -d --build
```

Ou use o helper:

```bash
bash scripts/vps/deploy.sh
```

Migrations e seed rodam automaticamente a cada deploy (seed é idempotente).

---

## Operação

### Logs

```bash
docker compose logs -f                  # todos
docker compose logs -f web nginx        # app + proxy
docker compose logs -f worker beat      # filas
```

Logs rotacionados (`json-file`, 20MB × 5 arquivos por serviço).

### Status / health

```bash
docker compose ps
curl -fsS http://127.0.0.1/healthz
curl -fsS http://127.0.0.1/api/v1/health
curl -fsS http://127.0.0.1/api/v1/health/ready
```

### Reinício

```bash
docker compose restart
# ou serviço específico:
docker compose restart web worker
```

### Parar / subir

```bash
docker compose down          # mantém volumes (dados)
docker compose up -d --build
```

### Backup

```bash
bash scripts/vps/backup.sh
# gera: backups/erp_<db>_<timestamp>.sql.gz
```

Agende no cron (exemplo diário às 03:15 UTC):

```bash
crontab -e
# 15 3 * * * cd /opt/erp-locadora && bash scripts/vps/backup.sh >> /var/log/erp-backup.log 2>&1
```

### Restore

```bash
bash scripts/vps/restore.sh backups/erp_erp_YYYYMMDDTHHMMSSZ.sql.gz
docker compose up -d
```

### Rollback

```bash
# 1) Código
git log --oneline -n 10
git checkout <commit_anterior>
docker compose up -d --build

# 2) Dados (se necessário)
bash scripts/vps/restore.sh backups/<arquivo>.sql.gz
docker compose up -d
```

---

## Arquitetura dos containers

| Serviço | Função | Restart |
|---|---|---|
| `db` | PostgreSQL 16 + role NOSUPERUSER (RLS) | unless-stopped |
| `redis` | Cache / broker Celery (AOF + senha) | unless-stopped |
| `migrate` | `alembic upgrade head` (one-shot) | on-failure |
| `seed` | seed idempotente (one-shot) | on-failure |
| `web` | Gunicorn + Uvicorn | unless-stopped |
| `worker` | Celery worker | unless-stopped |
| `beat` | Celery beat | unless-stopped |
| `nginx` | Proxy HTTP porta 80 | unless-stopped |

Volumes persistentes: `erp_pgdata`, `erp_redisdata`.  
Rede interna: `erp_net` (Postgres/Redis **não** são publicados na internet).

---

## Arquitetura da aplicação (inalterada)

- Clean Architecture · DDD · SOLID · Repository · Service Layer · Unit of Work
- Feature-first em `app/modules/*`
- Multiempresa (`tenant_id` + RLS) e multifilial
- RBAC `modulo.recurso.acao`
- Web HTML + API REST `/api/v1` compartilhar services

---

## Estrutura relevante

```
docker/
  Dockerfile
  entrypoint.sh
  nginx/default.conf
  postgres/init-app-role.sh
scripts/
  seed.py
  vps/
    setup-ubuntu.sh
    deploy.sh
    backup.sh
    restore.sh
docker-compose.yml
.env.example
```

---

## Segurança (checklist VPS)

1. Firewall UFW com 22/80/443 apenas.
2. Senhas fortes no `.env` (nunca commitadas).
3. App conecta como `erp_app` (NOSUPERUSER) — RLS efetivo.
4. Redis com `requirepass`.
5. Nginx como único ponto de entrada; app na rede interna.
6. TLS (Cloudflare Flexible/Full ou Certbot) + `SESSION_HTTPS_ONLY=true`.
7. Backups diários fora do servidor (copie `backups/` para object storage).

---

## Roadmap funcional

Fase 0 (fundação) concluída. Próximas fases de produto não dependem desta adaptação de infraestrutura.
