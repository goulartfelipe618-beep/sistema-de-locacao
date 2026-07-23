"""Proxy seguro: site estático → ERP API pública (API Key só no servidor)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings

app = FastAPI(
    title="Site BFF",
    description="Backend-for-Frontend entre o site institucional e o ERP (white-label).",
    version="2.0.0",
    docs_url="/bff/docs" if "localhost" in settings.site_public_url else None,
    openapi_url="/bff/openapi.json" if "localhost" in settings.site_public_url else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


def _erp_headers(scope: str = "catalogo:read") -> dict[str, str]:
    api_key = settings.api_key_for_scope(scope)
    if not api_key:
        raise HTTPException(status_code=503, detail="BFF não configurado (ERP_API_KEY ausente).")
    return {
        "X-API-Key": api_key,
        "X-Tenant-Slug": settings.erp_tenant_slug.strip(),
        "Accept": "application/json",
    }


async def _erp_request(
    method: str,
    path: str,
    *,
    scope: str = "catalogo:read",
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    url = settings.erp_api_base + path
    try:
        async with httpx.AsyncClient(timeout=settings.bff_request_timeout_seconds) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=_erp_headers(scope),
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="ERP demorou para responder.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível contactar o ERP.") from exc

    if response.status_code >= 400:
        detail = "Erro na API do ERP."
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("message"):
                detail = str(body["message"])
            elif isinstance(body, dict) and body.get("detail"):
                detail = str(body["detail"])
        except Exception:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)

    if response.status_code == 204:
        return None
    return response.json()


@app.get("/bff/health")
async def bff_health() -> dict[str, object]:
    issues = settings.config_issues
    erp_status = "unknown"
    if not issues:
        try:
            await _erp_request("GET", "/api/v1/public/ping")
            erp_status = "ok"
        except HTTPException as exc:
            erp_status = f"error:{exc.status_code}"
        except Exception:
            erp_status = "unreachable"
    else:
        erp_status = "misconfigured"
    return {
        "status": "ok" if erp_status == "ok" and not issues else "degraded",
        "service": "site-bff",
        "erp": settings.erp_api_base,
        "tenant": settings.erp_tenant_slug,
        "erp_status": erp_status,
        "issues": issues,
    }


@app.get("/bff/ping")
async def bff_ping() -> Any:
    return await _erp_request("GET", "/api/v1/public/ping")


@app.get("/bff/empresa")
async def bff_empresa() -> Any:
    return await _erp_request("GET", "/api/v1/public/empresa")


@app.get("/bff/filiais")
async def bff_filiais() -> Any:
    return await _erp_request("GET", "/api/v1/public/filiais")


def _normalize_grupo_imagem_url(imagem_url: str | None) -> str | None:
    if not imagem_url:
        return None
    prefix = "/api/v1/public/veiculos/"
    if imagem_url.startswith(prefix) and imagem_url.endswith("/capa/imagem"):
        veiculo_id = imagem_url[len(prefix) : -len("/capa/imagem")]
        if veiculo_id:
            return f"/bff/veiculos/{veiculo_id}/capa/imagem"
    return imagem_url


def _normalize_grupos_payload(payload: Any) -> Any:
    if not isinstance(payload, list):
        return payload
    normalized: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["imagem_url"] = _normalize_grupo_imagem_url(row.get("imagem_url"))
        normalized.append(row)
    return normalized


@app.get("/bff/grupos")
async def bff_grupos(request: Request) -> Any:
    params = dict(request.query_params)
    payload = await _erp_request("GET", "/api/v1/public/grupos", params=params or None)
    return _normalize_grupos_payload(payload)


def _normalize_slides_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        slides = payload
    elif isinstance(payload, dict):
        raw = payload.get("slides") or payload.get("items")
        slides = raw if isinstance(raw, list) else []
    else:
        slides = []
    normalized: list[dict[str, Any]] = []
    for slide in slides:
        if not isinstance(slide, dict) or not slide.get("id"):
            continue
        item = dict(slide)
        item["imagem_url"] = f"/bff/slides/{slide['id']}/imagem"
        normalized.append(item)
    return normalized


@app.get("/bff/catalog")
async def bff_catalog() -> JSONResponse:
    """Empresa + filiais + slides em uma única ida ao ERP (menos latência no boot do site)."""
    empresa, filiais, slides_raw = await asyncio.gather(
        _erp_request("GET", "/api/v1/public/empresa"),
        _erp_request("GET", "/api/v1/public/filiais"),
        _erp_request("GET", "/api/v1/public/slides"),
    )
    payload = {
        "empresa": empresa,
        "filiais": filiais,
        "slides": _normalize_slides_payload(slides_raw),
    }
    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=120"},
    )


@app.get("/bff/slides")
async def bff_slides() -> list[dict[str, Any]]:
    payload = await _erp_request("GET", "/api/v1/public/slides")
    return _normalize_slides_payload(payload)


@app.get("/bff/slides/{slide_id}/imagem")
async def bff_slide_imagem(slide_id: str) -> Response:
    url = f"{settings.erp_api_base}/api/v1/public/slides/{slide_id}/imagem"
    headers = _erp_headers("catalogo:read")
    headers["Accept"] = "*/*"
    try:
        async with httpx.AsyncClient(timeout=settings.bff_request_timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="ERP demorou para responder.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível contactar o ERP.") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Imagem indisponível")

    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"},
    )


@app.get("/bff/veiculos/{veiculo_id}/capa/imagem")
async def bff_veiculo_capa_imagem(veiculo_id: str) -> Response:
    url = f"{settings.erp_api_base}/api/v1/public/veiculos/{veiculo_id}/capa/imagem"
    headers = _erp_headers("veiculos:read")
    headers["Accept"] = "*/*"
    try:
        async with httpx.AsyncClient(timeout=settings.bff_request_timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="ERP demorou para responder.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível contactar o ERP.") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Imagem indisponível")

    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"},
    )


def _normalize_veiculo_imagem_url(imagem_url: str | None) -> str | None:
    return _normalize_grupo_imagem_url(imagem_url)


def _normalize_veiculos_payload(payload: Any) -> Any:
    if not isinstance(payload, list):
        return payload
    normalized: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["imagem_url"] = _normalize_veiculo_imagem_url(row.get("imagem_url"))
        normalized.append(row)
    return normalized


@app.get("/bff/veiculos")
async def bff_veiculos(request: Request) -> Any:
    params = dict(request.query_params)
    payload = await _erp_request(
        "GET", "/api/v1/public/veiculos", scope="veiculos:read", params=params or None
    )
    return _normalize_veiculos_payload(payload)


@app.get("/bff/disponibilidade")
async def bff_disponibilidade(request: Request) -> Any:
    params = dict(request.query_params)
    return await _erp_request(
        "GET",
        "/api/v1/public/disponibilidade",
        scope="disponibilidade:read",
        params=params or None,
    )


@app.post("/bff/cotacao")
async def bff_cotacao(request: Request) -> Any:
    body = await request.json()
    return await _erp_request(
        "POST", "/api/v1/public/cotacao", scope="pricing:read", json_body=body
    )


@app.post("/bff/reservas")
async def bff_reservas(request: Request) -> Any:
    body = await request.json()
    return await _erp_request(
        "POST", "/api/v1/public/reservas/site", scope="reservas:write", json_body=body
    )


@app.post("/bff/atendimento")
async def bff_atendimento(request: Request) -> Any:
    """Encaminha o formulário de atendimento do site para o webhook do ERP."""
    webhook_url = settings.site_atendimento_webhook_url.strip()
    if not webhook_url:
        raise HTTPException(
            status_code=503,
            detail="SITE_ATENDIMENTO_WEBHOOK_URL não configurado no serviço site.",
        )
    body = await request.json()
    try:
        async with httpx.AsyncClient(timeout=settings.bff_request_timeout_seconds) as client:
            response = await client.post(
                webhook_url,
                json=body,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="ERP demorou para responder.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível contactar o webhook.") from exc

    if response.status_code >= 400:
        detail = "Erro ao registrar atendimento."
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("message") or payload.get("detail") or detail)
        except Exception:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)

    if response.status_code == 204 or not response.content:
        return {"ok": True}
    try:
        return response.json()
    except Exception:
        return {"ok": True}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": exc.detail})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.bff_host,
        port=settings.bff_port,
        reload=True,
    )
