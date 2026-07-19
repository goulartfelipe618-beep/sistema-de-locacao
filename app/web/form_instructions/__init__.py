"""Instruções de formulário — agregador central."""

from __future__ import annotations

from app.web.form_instructions._helpers import FormInstruction
from app.web.form_instructions.content_cadastros import INSTRUCTIONS as CADASTROS
from app.web.form_instructions.content_comercial import INSTRUCTIONS as COMERCIAL
from app.web.form_instructions.content_financeiro import INSTRUCTIONS as FINANCEIRO
from app.web.form_instructions.content_fiscal import INSTRUCTIONS as FISCAL
from app.web.form_instructions.content_frota import INSTRUCTIONS as FROTA
from app.web.form_instructions.content_intermediacao import INSTRUCTIONS as INTERMEDIACAO
from app.web.form_instructions.content_manutencao import INSTRUCTIONS as MANUTENCAO
from app.web.form_instructions.content_operacional import INSTRUCTIONS as OPERACIONAL
from app.web.form_instructions.content_sistema import INSTRUCTIONS as SISTEMA
from app.web.form_instructions.content_tarifario import INSTRUCTIONS as TARIFARIO

INSTRUCTIONS: dict[str, FormInstruction] = {
    **CADASTROS,
    **FROTA,
    **OPERACIONAL,
    **TARIFARIO,
    **INTERMEDIACAO,
    **FINANCEIRO,
    **FISCAL,
    **MANUTENCAO,
    **COMERCIAL,
    **SISTEMA,
}


def get_form_instruction(key: str) -> dict | None:
    """Retorna instruções do formulário pela chave ou None se não existir."""
    return INSTRUCTIONS.get(key)
