"""Utilitários para execução E2E do plano teste.md (Supabase real)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app

TZ = ZoneInfo("America/Sao_Paulo")
_CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


def d_plus(days: int, hour: int = 10, minute: int = 0) -> datetime:
    """Data/hora local D+N às HH:MM (teste.md)."""
    base = datetime.now(TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base + timedelta(days=days)


def today_local() -> date:
    return datetime.now(TZ).date()


def extract_csrf(html: str) -> str:
    match = _CSRF_RE.search(html)
    if not match:
        raise RuntimeError("csrf_token não encontrado no HTML")
    return match.group(1)


@dataclass
class StepResult:
    code: str
    name: str
    ok: bool
    detail: str = ""


@dataclass
class E2EContext:
    """IDs criados durante o fluxo linear."""

    filial_matriz_id: uuid.UUID | None = None
    filial_campinas_id: uuid.UUID | None = None
    cliente_pf_id: uuid.UUID | None = None
    cliente_pj_id: uuid.UUID | None = None
    motorista_id: uuid.UUID | None = None
    parceiro_id: uuid.UUID | None = None
    fornecedor_id: uuid.UUID | None = None
    vendedor_id: uuid.UUID | None = None
    marca_id: uuid.UUID | None = None
    modelo_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    combustivel_id: uuid.UUID | None = None
    acessorio_id: uuid.UUID | None = None
    veiculo_a_id: uuid.UUID | None = None
    veiculo_b_id: uuid.UUID | None = None
    tabela_id: uuid.UUID | None = None
    protecao_id: uuid.UUID | None = None
    taxa_id: uuid.UUID | None = None
    politica_id: uuid.UUID | None = None
    peca_id: uuid.UUID | None = None
    os_id: uuid.UUID | None = None
    pneu_id: uuid.UUID | None = None
    cupom_id: uuid.UUID | None = None
    oportunidade_id: uuid.UUID | None = None
    proposta_id: uuid.UUID | None = None
    campanha_id: uuid.UUID | None = None
    cotacao_id: uuid.UUID | None = None
    reserva_cotacao_id: uuid.UUID | None = None
    reserva_manual_id: uuid.UUID | None = None
    contrato_reserva_id: uuid.UUID | None = None
    contrato_balcao_id: uuid.UUID | None = None
    caixa_sessao_id: uuid.UUID | None = None
    receber_id: uuid.UUID | None = None
    pagar_id: uuid.UUID | None = None
    nfse_id: uuid.UUID | None = None
    nfe_id: uuid.UUID | None = None
    api_key: str | None = None
    auditor_role_id: uuid.UUID | None = None
    dispositivo_id: uuid.UUID | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class E2ERunner:
    """Orquestra passos via API REST + rotas web autenticadas."""

    def __init__(self) -> None:
        self.client = TestClient(app, raise_server_exceptions=False)
        self.ctx = E2EContext()
        self.results: list[StepResult] = []
        self._token: str | None = None
        self._web_logged_in = False

    # ------------------------------------------------------------------ logging
    def step(self, code: str, name: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            self.results.append(StepResult(code, name, True))
            print(f"  [x] {code} — {name}")
        except Exception as exc:
            msg = str(exc)
            self.results.append(StepResult(code, name, False, msg))
            print(f"  [!] {code} — {name}: {msg}")

    def skip(self, code: str, name: str, reason: str) -> None:
        self.results.append(StepResult(code, name, True, f"SKIP: {reason}"))
        print(f"  [~] {code} — {name} (skip: {reason})")

    # ------------------------------------------------------------------ auth
    def api_login(self, email: str, password: str) -> None:
        r = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if r.status_code != 200:
            raise RuntimeError(f"login API {r.status_code}: {r.text[:300]}")
        body = r.json()
        if body.get("requires_2fa"):
            raise RuntimeError("2FA ativo — desative para E2E")
        self._token = body["access_token"]

    def web_login(self, email: str, password: str) -> None:
        page = self.client.get("/login")
        csrf = extract_csrf(page.text)
        r = self.client.post(
            "/login",
            data={"csrf_token": csrf, "email": email, "password": password},
            follow_redirects=False,
        )
        if r.status_code not in (303, 302):
            raise RuntimeError(f"login web {r.status_code}: {r.text[:200]}")
        self._web_logged_in = True

    def web_logout(self) -> None:
        if not self._web_logged_in:
            return
        page = self.client.get("/")
        csrf = extract_csrf(page.text)
        self.client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
        self._web_logged_in = False

    def _auth_headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("API não autenticada")
        return {"Authorization": f"Bearer {self._token}"}

    # ------------------------------------------------------------------ HTTP
    def api(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        expected: int | tuple[int, ...] = 200,
    ) -> Any:
        r = self.client.request(
            method,
            path,
            json=json,
            params=params,
            headers=self._auth_headers(),
        )
        codes = (expected,) if isinstance(expected, int) else expected
        if r.status_code not in codes:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
        if r.status_code == 204:
            return None
        if "application/json" in r.headers.get("content-type", ""):
            return r.json()
        return r.text

    def web_get(self, path: str, *, expected: int = 200) -> str:
        r = self.client.get(path)
        if r.status_code != expected:
            raise RuntimeError(f"GET {path} -> {r.status_code}")
        return r.text

    def web_post_form(self, path: str, data: dict[str, Any], *, from_path: str = "/") -> None:
        page = self.client.get(from_path)
        csrf = extract_csrf(page.text)
        payload = {"csrf_token": csrf, **data}
        r = self.client.post(path, data=payload, follow_redirects=False)
        if r.status_code not in (200, 303, 302):
            raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:300]}")

    def web_post_json(self, path: str, payload: dict, *, from_path: str = "/") -> Any:
        page = self.client.get(from_path)
        csrf = extract_csrf(page.text)
        r = self.client.post(
            path,
            json=payload,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"POST JSON {path} -> {r.status_code}: {r.text[:300]}")
        if "application/json" in r.headers.get("content-type", ""):
            return r.json()
        return r.text

    # ------------------------------------------------------------------ helpers
    def find_cliente(self, q: str) -> uuid.UUID | None:
        data = self.api("GET", "/api/v1/cadastros/clientes", params={"q": q, "size": 5})
        items = data.get("items") or []
        return uuid.UUID(items[0]["id"]) if items else None

    def find_veiculo_placa(self, placa: str) -> uuid.UUID | None:
        data = self.api("GET", "/api/v1/frota/veiculos", params={"q": placa, "size": 5})
        items = data.get("items") or []
        for item in items:
            if item.get("placa", "").upper().replace("-", "") == placa.upper().replace("-", ""):
                return uuid.UUID(item["id"])
        return uuid.UUID(items[0]["id"]) if items else None

    def find_filial_code(self, code: str) -> uuid.UUID | None:
        data = self.api("GET", "/api/v1/branches", params={"size": 50})
        for item in data.get("data") or []:
            if item.get("code") == code:
                return uuid.UUID(item["id"])
        return None

    def gerar_pdf(self, template_id: str, entidade_id: uuid.UUID) -> None:
        self.api(
            "POST",
            "/api/v1/documentos/gerar",
            json={"template_id": template_id, "entidade_id": str(entidade_id), "sincrono": True},
            expected=(200, 201, 202),
        )

    def emitir_relatorio(self, categoria: str, codigo: str, params: dict | None = None) -> None:
        payload = {
            "categoria": categoria,
            "relatorio_codigo": codigo,
            "formato": "pdf",
            "parametros": params or {},
            "usar_cache": False,
        }
        emissao = self.api("POST", "/api/v1/relatorios/emitir", json=payload, expected=(200, 201))
        em_id = emissao["id"]
        for _ in range(30):
            detail = self.api("GET", f"/api/v1/relatorios/emissoes/{em_id}")
            if detail["status"] in ("concluido", "erro"):
                if detail["status"] == "erro":
                    raise RuntimeError(detail.get("erro_mensagem") or "relatório falhou")
                return
        raise RuntimeError(f"timeout relatório {codigo}")

    def menu_urls_smoke(self) -> None:
        from app.web.navigation import NAVIGATION

        def collect(items: tuple) -> list[str]:
            urls: list[str] = []
            for item in items:
                if getattr(item, "url", None) and getattr(item, "implemented", False):
                    urls.append(item.url)
                if getattr(item, "items", None):
                    for sub in item.items:
                        if sub.url and sub.implemented:
                            urls.append(sub.url)
            return urls

        for section in NAVIGATION:
            if section.url and section.implemented:
                self.web_get(section.url)
            for url in collect((section,)):
                if url != section.url:
                    self.web_get(url)

    def summary(self) -> tuple[int, int, list[StepResult]]:
        ok = sum(1 for r in self.results if r.ok)
        fail = [r for r in self.results if not r.ok]
        return ok, len(self.results), fail
