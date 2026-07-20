"""Testes das instruções de formulário."""

from __future__ import annotations

from app.web.form_instructions import INSTRUCTIONS, get_form_instruction


def test_all_instructions_have_required_sections() -> None:
    assert len(INSTRUCTIONS) >= 58
    for key, data in INSTRUCTIONS.items():
        assert data["intro"].strip(), key
        assert len(data["sections"]) >= 5, key
        for section in data["sections"]:
            assert section["heading"].strip(), key
            assert len(section["items"]) >= 3, key


def test_form_instructions_macro_renders_sections() -> None:
    from app.web.form_instructions import get_form_instruction

    data = get_form_instruction("cadastros.cliente")
    assert data is not None
    section = data["sections"][0]
    assert isinstance(section["items"], list)
    assert len(section["items"]) >= 3


def test_get_form_instruction_known_key() -> None:
    data = get_form_instruction("cadastros.cliente")
    assert data is not None
    assert "Cliente" in data["intro"] or "cliente" in data["intro"].lower()


def test_get_form_instruction_unknown_key() -> None:
    assert get_form_instruction("inexistente.xyz") is None


def test_list_templates_import_list_create_actions() -> None:
    from pathlib import Path

    root = Path("app")
    missing: list[str] = []
    for path in root.rglob("*_list.html"):
        text = path.read_text(encoding="utf-8")
        if "list_create_actions(" not in text:
            continue
        if "macros/form_instructions.html" not in text:
            missing.append(str(path))
    assert not missing, "Import faltante em: " + ", ".join(missing)


def test_instruction_macros_registered_as_globals() -> None:
    from app.core.templating import templates

    for name in ("list_create_actions", "form_instructions", "form_page_header"):
        assert name in templates.env.globals, name
