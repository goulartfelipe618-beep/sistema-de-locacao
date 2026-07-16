"""Simulador de gateway de pagamentos (§12.1)."""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any

from app.modules.integracoes.adapters.payment_port import PagamentoWebhookPayload
from app.shared.enums import PagamentoWebhookEvento


class SimuladorPagamento:
    nome = "simulador"

    def validar_assinatura(self, *, body: bytes, signature: str, secret: str) -> bool:
        if not signature or not secret:
            return False
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.strip())

    def parse_webhook(self, *, body: bytes) -> PagamentoWebhookPayload:
        data: dict[str, Any] = json.loads(body.decode() or "{}")
        evento_raw = str(data.get("evento", "pago")).lower()
        try:
            evento = PagamentoWebhookEvento(evento_raw)
        except ValueError:
            evento = PagamentoWebhookEvento.PAGO
        valor = data.get("valor")
        return PagamentoWebhookPayload(
            evento=evento,
            referencia_externa=str(data.get("referencia", data.get("txid", ""))),
            valor=Decimal(str(valor)) if valor is not None else None,
            metodo=data.get("metodo"),
            raw=data,
        )

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        return bool(credenciais.get("client_id") or credenciais.get("api_key"))
