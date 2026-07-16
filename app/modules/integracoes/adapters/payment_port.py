"""Porta (Protocol) de gateway de pagamentos (§12.1)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from app.shared.enums import PagamentoWebhookEvento


@dataclass(slots=True)
class PagamentoWebhookPayload:
    evento: PagamentoWebhookEvento
    referencia_externa: str
    valor: Decimal | None = None
    metodo: str | None = None
    raw: dict[str, Any] | None = None


@runtime_checkable
class PaymentGatewayPort(Protocol):
    """Contrato de gateway/adquirente/PSP."""

    nome: str

    def validar_assinatura(self, *, body: bytes, signature: str, secret: str) -> bool:
        """Valida assinatura HMAC do webhook."""
        ...

    def parse_webhook(self, *, body: bytes) -> PagamentoWebhookPayload:
        """Interpreta payload bruto do webhook."""
        ...

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        """Testa credenciais do provedor."""
        ...
