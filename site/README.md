# Site institucional Rodavia + BFF

Serviços:

| Serviço    | Porta host | Função                          |
|-----------|------------|----------------------------------|
| `site-web` | 8080       | Nginx — arquivos estáticos       |
| `site-bff` | 8090       | Proxy Python → ERP `/api/v1/public/*` |

## 1. Coloque os arquivos do site

Copie o HTML/CSS/JS que você já criou para `site/public/` (ou monte outro volume no Compose).

## 2. Configure o BFF

```bash
cd site
cp .env.example .env
# Edite ERP_API_KEY (Integrações → API pública no ERP, scopes: catalogo, veiculos, pricing, reservas)
```

## 3. Subir localmente

```bash
docker compose up -d --build
```

- Site: http://localhost:8080  
- BFF direto (debug): http://localhost:8090/bff/health  

No front, use **`/bff/...`** (mesma origem via Nginx), por exemplo:

```javascript
const API = "/bff"; // não use URL absoluta do ERP
fetch(API + "/empresa");
```

## 4. Trocar domínio depois

1. Aponte DNS do seu domínio para o servidor do site.
2. Atualize `site/.env`:
   - `SITE_PUBLIC_URL=https://www.seudominio.com.br`
   - `SITE_ALLOWED_ORIGINS=https://www.seudominio.com.br,https://seudominio.com.br`
3. Nginx/Certbot no host (HTTPS). Exemplo `server_name www.seudominio.com.br;`
4. **`ERP_BASE_URL`** continua sendo a URL do ERP (Easypanel ou subdomínio tipo `erp.seudominio.com.br`) — não precisa ser o mesmo domínio do site.
5. Regenerar chave API se rotacionar; nunca commitar `.env`.

## 5. Sem Docker (dev)

Terminal 1 — BFF:

```bash
cd site/bff
pip install -r requirements.txt
set ERP_API_KEY=erp_...   # Windows
python main.py
```

Terminal 2 — site estático (ex.: `npx serve public -p 8080`) e configure proxy manual ou CORS apontando `http://localhost:8090` (preferível Nginx ou proxy `/bff`).

## Endpoints BFF

| BFF | ERP |
|-----|-----|
| GET `/bff/ping` | `/api/v1/public/ping` |
| GET `/bff/empresa` | `/api/v1/public/empresa` |
| GET `/bff/filiais` | `/api/v1/public/filiais` |
| GET `/bff/grupos?filial_id&retirada_em&devolucao_em` | `/api/v1/public/grupos` |
| POST `/bff/cotacao` | `/api/v1/public/cotacao` |
| POST `/bff/reservas` | `/api/v1/public/reservas/site` |

## Segurança

- `ERP_API_KEY` só no container/processo BFF.
- Site estático não acessa JWT do ERP nem painel admin.
- Use HTTPS em produção no domínio do site.
