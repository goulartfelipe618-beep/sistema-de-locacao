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


def test_get_form_instruction_known_key() -> None:
    data = get_form_instruction("cadastros.cliente")
    assert data is not None
    assert "Cliente" in data["intro"] or "cliente" in data["intro"].lower()


def test_get_form_instruction_unknown_key() -> None:
    assert get_form_instruction("inexistente.xyz") is None
