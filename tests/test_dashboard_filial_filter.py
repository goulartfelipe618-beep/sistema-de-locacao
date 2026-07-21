"""Testes do filtro de filial no dashboard e query params."""

from __future__ import annotations

import uuid

from app.shared.query_params import parse_optional_uuid


def test_parse_optional_uuid_empty_values() -> None:
    assert parse_optional_uuid(None) is None
    assert parse_optional_uuid("") is None
    assert parse_optional_uuid("   ") is None


def test_parse_optional_uuid_valid() -> None:
    uid = uuid.uuid4()
    assert parse_optional_uuid(str(uid)) == uid


def test_parse_optional_uuid_invalid_returns_none() -> None:
    assert parse_optional_uuid("not-a-uuid") is None


def test_spa_nav_omits_empty_query_params() -> None:
    from pathlib import Path

    js = Path("app/web/static/js/spa-nav.js").read_text(encoding="utf-8")
    assert 'String(value).trim() !== ""' in js


def test_spa_nav_uses_longest_prefix_match() -> None:
    from pathlib import Path

    js = Path("app/web/static/js/spa-nav.js").read_text(encoding="utf-8")
    assert "navPathMatches" in js
    assert "bestLen" in js
    assert "pendingSpaUrl" in js
    assert "outerHTML" in js
    assert "pushSpaUrl" in js
    assert "history.pushState" in js


def test_dashboard_parses_filial_from_query_only() -> None:
    from pathlib import Path

    src = Path("app/modules/dashboard/web.py").read_text(encoding="utf-8")
    assert "parse_optional_uuid(request.query_params.get(\"filial_id\"))" in src
    assert "filial_id: uuid.UUID" not in src
    assert "list_all()" in src
