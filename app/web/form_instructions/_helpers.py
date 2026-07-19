"""Helpers para montar blocos de instrução de formulários."""

from __future__ import annotations

from typing import TypedDict


class InstructionSection(TypedDict):
    heading: str
    items: list[str]


class FormInstruction(TypedDict):
    intro: str
    sections: list[InstructionSection]


def instr(intro: str, *sections: tuple[str, list[str]]) -> FormInstruction:
    return {
        "intro": intro,
        "sections": [{"heading": heading, "items": items} for heading, items in sections],
    }
