"""Configuração e fixtures de teste.

Define variáveis de ambiente mínimas antes de importar a aplicação, garantindo
que os testes puros (sem infraestrutura) rodem de forma isolada.
"""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdefghijklmnopqrstuvwxyz-abcdef")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_JSON", "false")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Cliente HTTP de testes para a aplicação FastAPI."""
    with TestClient(app) as test_client:
        yield test_client
