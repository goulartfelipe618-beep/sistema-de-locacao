"""Testes do health check de liveness (não dependem de banco/redis)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_openapi_available(client: TestClient) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"]


def test_login_page_renders(client: TestClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert "Painel Administrativo" in response.text
