"""Portas (interfaces) para envio de e-mail e SMS."""

from __future__ import annotations

from typing import Protocol


class EmailPort(Protocol):
    """Contrato para provedores de e-mail."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        """Envia e-mail. Levanta exceção em falha."""


class SmsPort(Protocol):
    """Contrato para provedores de SMS."""

    def send(self, *, to: str, body: str) -> None:
        """Envia SMS. Levanta exceção em falha."""
