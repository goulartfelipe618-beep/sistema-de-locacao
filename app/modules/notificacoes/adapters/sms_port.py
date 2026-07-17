"""Porta (interface) para envio de SMS/WhatsApp."""

from __future__ import annotations

from typing import Protocol


class SmsPort(Protocol):
    def send(self, *, to: str, body: str) -> None: ...
