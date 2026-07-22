# Site institucional (white-label)

Site B2C da locadora — **serviço separado** do ERP, no mesmo repositório.

## Estrutura

```
site/
  public/          # HTML, CSS, JS estático
  bff/             # Proxy FastAPI → API pública do ERP
  nginx/           # Proxy /bff no mesmo container
  Dockerfile       # nginx + BFF (1 container = 1 serviço Easypanel)
```

## Comunicação com o ERP

O browser **nunca** chama o ERP diretamente. Fluxo:

1. JS chama `/bff/empresa`, `/bff/slides`, etc.
2. Nginx repassa para o BFF (porta 8090 interna).
3. BFF chama `http://web:8000/api/v1/public/...` (rede Docker) com `X-API-Key`.

Configure no `.env` da **raiz do repo** (ou no Easypanel, serviço site):

- `ERP_INTERNAL_URL` — URL interna do ERP
- `SITE_ERP_API_KEY` / `ERP_API_KEY` — chave da API pública
- `ERP_TENANT_SLUG` — slug do tenant (ex.: `matriz`)

Deploy completo: [docs/deploy/EASYPANEL-WHITELABEL.md](../docs/deploy/EASYPANEL-WHITELABEL.md)
