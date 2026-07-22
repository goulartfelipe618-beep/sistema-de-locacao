# Deploy white-label (Easypanel / Docker)

Um **projeto** por locadora: **ERP + Site + Postgres + Redis**, com **dois serviços de aplicação**:

| Serviço | Função | Porta |
|---------|--------|-------|
| `erp-locadora` (web) | Painel administrativo FastAPI | 8000 |
| `site` | Site público (nginx + BFF) | 80 |
| `postgres` | Banco de dados | 5432 |
| `redis` | Filas / cache | 6379 |

## ⚠️ Git push NÃO atualiza produção sozinho

O Easypanel **não redeploya automaticamente** (salvo webhook configurado).  
Depois de cada `git push`, é obrigatório **Implantar / Rebuild** em **cada serviço** que mudou.

**Como saber se atualizou:** abra  
`https://SEU-ERP/api/v1/health` → campo `"version"` deve bater com o GitHub (ex.: `0.2.8`).  
Se o rodapé ainda mostra `v0.2.6`, o container antigo ainda está rodando.

## Easypanel — atualizar serviço ERP (`erp-locadora`)

1. Abra o serviço **`erp-locadora`** (não o `site`).
2. Aba **Fonte** — confira:
   - Repositório: `goulartfelipe618-beep/sistema-de-locacao`
   - Branch: `main`
   - Caminho de Build: `/` (raiz)
   - Dockerfile: **`docker/Dockerfile`**
3. Clique **Implantar** (ou **Rebuild**) e aguarde ficar verde.
4. Valide: `GET /api/v1/health` → `"version":"0.2.8"` (ou a versão atual da `main`).

> O código fica **dentro da imagem Docker**. Só reiniciar o container **sem rebuild** mantém a versão antiga.

## Como o site fala com o ERP

```
Navegador → site:80/bff/* → BFF (FastAPI interno) → ERP:8000/api/v1/public/*
```

- A **API Key fica só no servidor** (variável `SITE_ERP_API_KEY` / `ERP_API_KEY` no serviço site).
- O BFF usa **rede interna**, não URL pública:
  - Docker Compose: `ERP_INTERNAL_URL=http://web:8000`
  - Easypanel: `ERP_INTERNAL_URL=http://erp-locadora:8000` (nome do serviço ERP)
- Tenant white-label: `ERP_TENANT_SLUG=matriz` (igual ao `DEFAULT_TENANT_SLUG` do ERP).

## Easypanel — adicionar serviço Site

1. No projeto, clique **+** em SERVIÇOS.
2. **App → Docker** (ou GitHub).
3. Repositório: `goulartfelipe618-beep/sistema-de-locacao`
4. **Build (escolha UMA opção):**

**Opção A — subpasta `site` (preferida se o Easypanel tiver Root Directory):**

| Campo | Valor |
|-------|--------|
| Root Directory / Source Path | `site` |
| Dockerfile | `Dockerfile` |

**Opção B — raiz do repo (se der erro `Dockerfile: no such file`):**

| Campo | Valor |
|-------|--------|
| Root Directory | *(vazio / raiz)* |
| Dockerfile | `Dockerfile.site` |

O arquivo `Dockerfile.site` na raiz do repositório existe para Easypanel que sempre faz build na raiz do clone.

5. **Porta exposta:** 80 (domínio público do site, ex.: `rodavia.com.br`). No Easypanel use **domínio**, não mapeie porta 80 do host duas vezes — cada container tem sua porta 80 interna.

   **⚠️ Porta interna do serviço `site` = `80`** (nginx).  
   **⚠️ Porta interna do serviço `erp-locadora` = `8000`** (Gunicorn).  
   Se o site mostrar **502 Service is not reachable**, a porta do serviço `site` provavelmente está errada (ex.: 8000 ou 8090).

6. **Variáveis de ambiente** (serviço `site`):

```env
ERP_INTERNAL_URL=http://erp-locadora:8000
ERP_TENANT_SLUG=matriz
ERP_API_KEY=erp_sua_chave_catalogo_read
SITE_PUBLIC_URL=https://www.sualocadora.com
SITE_ALLOWED_ORIGINS=https://www.sualocadora.com
```

> **Importante:** o tenant padrão do ERP é `matriz` (não `rodavia`). Use a chave de **catalogo:read** em `ERP_API_KEY`, ou defina `ERP_API_KEY_CATALOGO`.

7. Gere a API Key no ERP: **Integrações → API Pública** (escopos: `catalogo:read`, `veiculos:read`, `pricing:read`, `reservas:write`, `disponibilidade:read`).

## Docker Compose (VPS)

```bash
cp .env.example .env
# Preencha SITE_ERP_API_KEY e demais segredos
docker compose up -d --build
```

- ERP admin: `http://localhost` (porta 80, nginx → web)
- Site: `http://localhost:8080` (serviço `site`)

## Dev local

```powershell
# Terminal 1 — stack ERP
docker compose up db redis web

# Terminal 2 — site
cd site
pip install -r bff/requirements.txt
$env:ERP_INTERNAL_URL="http://127.0.0.1:8000"
$env:ERP_API_KEY="sua_chave"
$env:ERP_TENANT_SLUG="matriz"
python -m uvicorn bff.main:app --app-dir . --host 127.0.0.1 --port 8090

# Terminal 3 — estático (ou use site/Dockerfile)
cd site/public
python -m http.server 8080
```

Ou use `site/scripts/start-dev.ps1` (carrega `.env` da raiz do repo).

## Erro comum no Easypanel

```
failed to read dockerfile: open Dockerfile: no such file or directory
```

**Causa:** build apontando para a **raiz do repositório** em vez da pasta `site/`.

**Correção:** use **Opção B** — Dockerfile = `Dockerfile.site` (raiz do repo), depois **Rebuild**.

## Site com 502 "Service is not reachable"

**Causa 1 — porta errada no Easypanel (mais comum):** serviço `site` com porta **80**, não 8000/8090.

**Causa 2 — variáveis ausentes:** após o site subir, `/bff/*` pode falhar se faltar:

```env
ERP_INTERNAL_URL=http://erp-locadora:8000
ERP_TENANT_SLUG=matriz
ERP_API_KEY=erp_SUA_CHAVE_CATALOGO_READ
SITE_PUBLIC_URL=https://SEU-DOMINIO-DO-SITE
SITE_ALLOWED_ORIGINS=https://SEU-DOMINIO-DO-SITE
```

**Validar:** `https://SEU-SITE/bff/health` → `"erp_status":"ok"`.
