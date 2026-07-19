"""Smoke test: formulários de cadastro renderizam com Instruções."""
from __future__ import annotations

import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdefghijklmnopqrstuvwxyz-abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

from fastapi.testclient import TestClient

from app.main import app

PATHS = [
    "/cadastros/clientes/novo",
    "/cadastros/parceiros/novo",
    "/cadastros/fornecedores/novo",
    "/cadastros/clientes",
]


def main() -> None:
    with TestClient(app) as client:
        login_page = client.get("/login")
        m = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
        assert m, "csrf on login"
        client.post(
            "/login",
            data={
                "email": "admin@locadora.local",
                "password": "Admin@123",
                "csrf_token": m.group(1),
            },
            follow_redirects=True,
        )
        for path in PATHS:
            resp = client.get(path)
            ok = resp.status_code == 200
            instr = "form-instructions-btn" in resp.text
            print(f"{path} -> {resp.status_code} instructions={instr}")
            if not ok:
                print(resp.text[:800])


if __name__ == "__main__":
    main()
