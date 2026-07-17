"""Testes de preferência de tema da UI."""

from __future__ import annotations

from app.core.ui_theme import DEFAULT_UI_THEME, normalize_ui_theme


def test_normalize_ui_theme() -> None:
    assert normalize_ui_theme("dark") == "dark"
    assert normalize_ui_theme("light") == "light"
    assert normalize_ui_theme("hybrid") == "hybrid"
    assert normalize_ui_theme("invalid") == DEFAULT_UI_THEME
    assert normalize_ui_theme(None) == DEFAULT_UI_THEME
