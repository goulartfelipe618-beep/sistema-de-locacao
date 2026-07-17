"""Simulador de SMS (desenvolvimento / testes)."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class SimuladorSms:
    """Registra envios no log sem transmitir mensagens."""

    def send(self, *, to: str, body: str) -> None:
        logger.info("[SimuladorSms] to=%s body=%s", to, body[:120])
