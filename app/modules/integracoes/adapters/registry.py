"""Registry central de adaptadores de integração (§12)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.logging import get_logger
from app.modules.integracoes.adapters.credito_port import CreditoPort
from app.modules.integracoes.adapters.http_client import http_get_json, http_post_json
from app.modules.integracoes.adapters.http_telemetria import HttpTelemetriaAdapter
from app.modules.integracoes.adapters.payment_port import PagamentoWebhookPayload, PaymentGatewayPort
from app.modules.integracoes.adapters.simulador_credito import SimuladorCredito
from app.modules.integracoes.adapters.simulador_pagamento import SimuladorPagamento
from app.modules.integracoes.adapters.simulador_telemetria import SimuladorTelemetria
from app.modules.integracoes.adapters.simulador_transito import SimuladorTransito
from app.modules.integracoes.adapters.telemetria_port import TelemetriaPort
from app.modules.integracoes.adapters.transito_port import (
    CnhConsulta,
    DebitoVeicular,
    MultaTransito,
    TransitoPort,
)
from app.shared.enums import IntegracaoTipo, PagamentoWebhookEvento

logger = get_logger(__name__)

PROVEDORES_POR_TIPO: dict[str, tuple[str, ...]] = {
    "pagamentos": ("simulador", "mercadopago", "pagseguro"),
    "transito": ("simulador", "sintegra"),
    "credito": ("simulador", "serasa"),
    "telemetria": ("simulador", "http"),
}


class MercadoPagoAdapter(SimuladorPagamento):
    """Adapter Mercado Pago — validação HTTP + parse de webhook MP."""

    nome = "mercadopago"

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        token = credenciais.get("access_token") or credenciais.get("api_key")
        if not token or len(token) < 8:
            return False
        try:
            http_get_json(
                "https://api.mercadopago.com/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            return True
        except Exception:  # noqa: BLE001
            return len(token) >= 12

    def parse_webhook(self, *, body: bytes) -> PagamentoWebhookPayload:
        data: dict[str, Any] = json.loads(body.decode() or "{}")
        action = str(data.get("action", data.get("type", "pago"))).lower()
        evento = PagamentoWebhookEvento.PAGO
        if "refund" in action or "chargeback" in action:
            evento = PagamentoWebhookEvento.CHARGEBACK if "chargeback" in action else PagamentoWebhookEvento.ESTORNADO
        elif "authorized" in action:
            evento = PagamentoWebhookEvento.AUTORIZADO
        elif "captured" in action:
            evento = PagamentoWebhookEvento.CAPTURADO
        nested = data.get("data") if isinstance(data.get("data"), dict) else {}
        ref = str(
            nested.get("id")
            or data.get("external_reference")
            or data.get("referencia")
            or data.get("txid")
            or ""
        )
        valor = data.get("valor") or nested.get("transaction_amount")
        return PagamentoWebhookPayload(
            evento=evento,
            referencia_externa=ref,
            valor=Decimal(str(valor)) if valor is not None else None,
            metodo="mercadopago",
            raw=data,
        )


class PagSeguroAdapter(SimuladorPagamento):
    """Adapter PagSeguro — validação de credenciais + parse de notificação."""

    nome = "pagseguro"

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        email = credenciais.get("email")
        token = credenciais.get("token") or credenciais.get("api_key")
        if not email or not token:
            return False
        try:
            http_get_json(
                f"https://ws.pagseguro.uol.com.br/v2/sessions?email={email}&token={token}",
            )
            return True
        except Exception:  # noqa: BLE001
            return len(token) >= 8

    def parse_webhook(self, *, body: bytes) -> PagamentoWebhookPayload:
        data: dict[str, Any] = json.loads(body.decode() or "{}")
        status = str(data.get("status", data.get("evento", "pago"))).lower()
        evento = PagamentoWebhookEvento.PAGO
        if status in {"cancelled", "refunded", "estornado"}:
            evento = PagamentoWebhookEvento.ESTORNADO
        elif status in {"chargeback", "dispute"}:
            evento = PagamentoWebhookEvento.CHARGEBACK
        ref = str(data.get("reference", data.get("txid", data.get("notificationCode", ""))))
        valor = data.get("valor") or data.get("grossAmount")
        return PagamentoWebhookPayload(
            evento=evento,
            referencia_externa=ref,
            valor=Decimal(str(valor)) if valor is not None else None,
            metodo="pagseguro",
            raw=data,
        )


class SerasaAdapter(SimuladorCredito):
    """Adapter Serasa — consulta HTTP configurável com fallback simulado."""

    nome = "serasa"

    def consultar_score(self, *, documento: str, tipo_pessoa: str, credenciais: dict[str, str]):
        if not credenciais.get("api_key") and not credenciais.get("client_id"):
            raise ValueError("Credenciais Serasa ausentes (api_key ou client_id).")
        base = (credenciais.get("base_url") or credenciais.get("api_url") or "").strip()
        if base:
            try:
                headers = {"Accept": "application/json"}
                if credenciais.get("api_key"):
                    headers["Authorization"] = f"Bearer {credenciais['api_key']}"
                data = http_post_json(
                    f"{base.rstrip('/')}/score",
                    payload={"documento": documento, "tipo_pessoa": tipo_pessoa},
                    headers=headers,
                )
                from app.modules.integracoes.adapters.credito_port import CreditoConsultaResultado

                return CreditoConsultaResultado(
                    score=int(data.get("score", 600)),
                    restricao=bool(data.get("restricao", False)),
                    motivo=data.get("motivo"),
                    bureau="serasa",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Serasa HTTP falhou (%s); usando simulador.", exc)
        return super().consultar_score(
            documento=documento, tipo_pessoa=tipo_pessoa, credenciais=credenciais
        )


class SintegraTransitoAdapter(SimuladorTransito):
    """Adapter agregador veicular — consultas HTTP com fallback simulado."""

    nome = "sintegra"

    def _base_url(self, credenciais: dict[str, str]) -> str:
        return (credenciais.get("base_url") or credenciais.get("api_url") or "").strip()

    def _headers(self, credenciais: dict[str, str]) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        key = credenciais.get("api_key") or credenciais.get("client_id")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        base = self._base_url(credenciais)
        if not base:
            return bool(credenciais.get("api_key") or credenciais.get("client_id"))
        try:
            http_get_json(f"{base.rstrip('/')}/health", headers=self._headers(credenciais))
            return True
        except Exception:  # noqa: BLE001
            return bool(credenciais.get("api_key"))

    def consultar_multas_veiculo(
        self, *, placa: str, renavam: str | None, credenciais: dict[str, str]
    ) -> list[MultaTransito]:
        base = self._base_url(credenciais)
        if base:
            try:
                data = http_post_json(
                    f"{base.rstrip('/')}/multas",
                    payload={"placa": placa, "renavam": renavam},
                    headers=self._headers(credenciais),
                )
                return self._parse_multas(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Sintegra multas HTTP falhou (%s); simulador.", exc)
        return super().consultar_multas_veiculo(
            placa=placa, renavam=renavam, credenciais=credenciais
        )

    def consultar_cnh(
        self, *, cnh_numero: str, cpf: str | None, credenciais: dict[str, str]
    ) -> CnhConsulta:
        base = self._base_url(credenciais)
        if base:
            try:
                data = http_post_json(
                    f"{base.rstrip('/')}/cnh",
                    payload={"cnh": cnh_numero, "cpf": cpf},
                    headers=self._headers(credenciais),
                )
                return CnhConsulta(
                    numero=cnh_numero,
                    categoria=str(data.get("categoria", "B")),
                    validade=datetime.fromisoformat(data["validade"]) if data.get("validade") else None,
                    pontuacao=int(data.get("pontuacao", 0)),
                    status=str(data.get("status", "regular")),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Sintegra CNH HTTP falhou (%s); simulador.", exc)
        return super().consultar_cnh(cnh_numero=cnh_numero, cpf=cpf, credenciais=credenciais)

    def consultar_debitos_veiculo(
        self, *, placa: str, renavam: str | None, credenciais: dict[str, str]
    ) -> list[DebitoVeicular]:
        base = self._base_url(credenciais)
        if base:
            try:
                data = http_post_json(
                    f"{base.rstrip('/')}/debitos",
                    payload={"placa": placa, "renavam": renavam},
                    headers=self._headers(credenciais),
                )
                return self._parse_debitos(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Sintegra débitos HTTP falhou (%s); simulador.", exc)
        return super().consultar_debitos_veiculo(
            placa=placa, renavam=renavam, credenciais=credenciais
        )

    @staticmethod
    def _parse_multas(data: dict[str, Any]) -> list[MultaTransito]:
        items = data.get("multas", data.get("items", []))
        result: list[MultaTransito] = []
        for raw in items:
            ocorrido = raw.get("ocorrido_em")
            if isinstance(ocorrido, str):
                ocorrido_em = datetime.fromisoformat(ocorrido.replace("Z", "+00:00"))
            else:
                ocorrido_em = datetime.now(tz=UTC)
            result.append(
                MultaTransito(
                    ait=str(raw.get("ait", "")),
                    codigo_infracao=str(raw.get("codigo_infracao", "")),
                    orgao=str(raw.get("orgao", "DETRAN")),
                    valor=Decimal(str(raw.get("valor", "0"))),
                    pontuacao=int(raw.get("pontuacao", 0)),
                    ocorrido_em=ocorrido_em,
                )
            )
        return result

    @staticmethod
    def _parse_debitos(data: dict[str, Any]) -> list[DebitoVeicular]:
        items = data.get("debitos", data.get("items", []))
        result: list[DebitoVeicular] = []
        for raw in items:
            venc = raw.get("vencimento")
            vencimento = (
                datetime.fromisoformat(venc.replace("Z", "+00:00")) if isinstance(venc, str) else None
            )
            result.append(
                DebitoVeicular(
                    tipo=str(raw.get("tipo", "DEBITO")),
                    descricao=str(raw.get("descricao", "")),
                    valor=Decimal(str(raw.get("valor", "0"))),
                    vencimento=vencimento,
                )
            )
        return result


_PAYMENT: dict[str, type] = {
    "simulador": SimuladorPagamento,
    "mercadopago": MercadoPagoAdapter,
    "pagseguro": PagSeguroAdapter,
}

_TRANSITO: dict[str, type] = {
    "simulador": SimuladorTransito,
    "sintegra": SintegraTransitoAdapter,
}

_CREDITO: dict[str, type] = {
    "simulador": SimuladorCredito,
    "serasa": SerasaAdapter,
}

_TELEMETRIA: dict[str, type] = {
    "simulador": SimuladorTelemetria,
    "http": HttpTelemetriaAdapter,
}


def get_payment_adapter(provedor: str) -> PaymentGatewayPort:
    cls = _PAYMENT.get(provedor, SimuladorPagamento)
    return cls()


def get_transito_adapter(provedor: str) -> TransitoPort:
    cls = _TRANSITO.get(provedor, SimuladorTransito)
    return cls()


def get_credito_adapter(provedor: str) -> CreditoPort:
    cls = _CREDITO.get(provedor, SimuladorCredito)
    return cls()


def get_telemetria_adapter(provedor: str) -> TelemetriaPort:
    cls = _TELEMETRIA.get(provedor, SimuladorTelemetria)
    return cls()


def get_adapter(tipo: IntegracaoTipo, provedor: str):
    """Resolve adapter por tipo e nome do provedor."""
    if tipo == IntegracaoTipo.PAGAMENTOS:
        return get_payment_adapter(provedor)
    if tipo == IntegracaoTipo.TRANSITO:
        return get_transito_adapter(provedor)
    if tipo == IntegracaoTipo.CREDITO:
        return get_credito_adapter(provedor)
    if tipo == IntegracaoTipo.TELEMETRIA:
        return get_telemetria_adapter(provedor)
    raise ValueError(f"Tipo de integração não suportado: {tipo}")
