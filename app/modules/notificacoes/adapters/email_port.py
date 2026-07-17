"""Porta (interface) para envio de e-mail."""

from __future__ import annotations

from typing import Protocol


class EmailPort(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...
