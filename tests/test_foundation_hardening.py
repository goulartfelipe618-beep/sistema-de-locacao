"""Testes de regressão da auditoria da Fase 0 (fundação endurecida)."""

from __future__ import annotations

import inspect

import pytest
from fastapi.dependencies.utils import get_dependant
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.deps import get_api_db_session, get_current_api_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.modules.identity.repository import UserRepository


def test_api_db_session_depends_on_jwt_auth_first() -> None:
    """Garante que a sessão API só abre depois da autenticação (RLS/GUC)."""
    dependant = get_dependant(path="/", call=get_api_db_session)
    dependency_calls = [dep.call for dep in dependant.dependencies]
    assert get_current_api_user in dependency_calls


def test_permission_query_excludes_soft_deleted_roles() -> None:
    """O SQL de permissões deve filtrar papéis/permissoes com soft delete."""
    source = inspect.getsource(UserRepository.get_permission_codes)
    assert "Role.deleted_at.is_(None)" in source
    assert "Permission.deleted_at.is_(None)" in source
    assert "join(Role" in source


def test_refresh_token_includes_superuser_claim() -> None:
    """Refresh e access devem carregar is_superuser de forma coerente."""
    refresh = create_refresh_token(
        "11111111-1111-1111-1111-111111111111",
        {"tenant_id": "22222222-2222-2222-2222-222222222222", "is_superuser": True},
    )
    payload = decode_token(refresh, expected_type="refresh")
    assert payload["is_superuser"] is True

    access = create_access_token(
        payload["sub"],
        {"tenant_id": payload["tenant_id"], "is_superuser": payload["is_superuser"]},
    )
    access_payload = decode_token(access, expected_type="access")
    assert access_payload["is_superuser"] is True


def test_production_rejects_insecure_secret() -> None:
    with pytest.raises((ValidationError, ValueError)):
        Settings(
            environment="production",
            secret_key="dev-secret-key-change-in-production-0123456789abcdefghijklmnopqrstuvwxyz",
            session_https_only=True,
            debug=False,
        )


def test_production_rejects_http_session_cookie() -> None:
    with pytest.raises((ValidationError, ValueError)):
        Settings(
            environment="production",
            secret_key="a" * 64,
            session_https_only=False,
            debug=False,
        )


def test_login_page_includes_csrf_token(client: TestClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert 'name="csrf_token"' in response.text
    assert "csrf-token" in response.text


def test_mutating_web_without_csrf_is_rejected(client: TestClient) -> None:
    client.get("/login")
    response = client.post("/logout", data={}, follow_redirects=False)
    assert response.status_code == 403
