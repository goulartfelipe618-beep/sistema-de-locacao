"""Simulador de e-mail (desenvolvimento / testes)."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class SimuladorEmail:
    """Registra envios no log sem transmitir mensagens."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("[SimuladorEmail] to=%s subject=%s body=%s", to, subject, body[:120])
