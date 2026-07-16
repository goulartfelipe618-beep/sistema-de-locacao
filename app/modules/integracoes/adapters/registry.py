"""Registry central de adaptadores de integração (§12)."""

from __future__ import annotations

from app.modules.integracoes.adapters.credito_port import CreditoPort
from app.modules.integracoes.adapters.payment_port import PaymentGatewayPort
from app.modules.integracoes.adapters.simulador_credito import SimuladorCredito
from app.modules.integracoes.adapters.simulador_pagamento import SimuladorPagamento
from app.modules.integracoes.adapters.simulador_telemetria import SimuladorTelemetria
from app.modules.integracoes.adapters.simulador_transito import SimuladorTransito
from app.modules.integracoes.adapters.telemetria_port import TelemetriaPort
from app.modules.integracoes.adapters.transito_port import TransitoPort
from app.shared.enums import IntegracaoTipo


class MercadoPagoAdapter(SimuladorPagamento):
    """Adapter Mercado Pago — valida credenciais; emissão simulada até API real."""

    nome = "mercadopago"

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        token = credenciais.get("access_token") or credenciais.get("api_key")
        return bool(token and len(token) >= 8)


class PagSeguroAdapter(SimuladorPagamento):
    """Adapter PagSeguro — valida credenciais; emissão simulada até API real."""

    nome = "pagseguro"

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        return bool(credenciais.get("email") and credenciais.get("token"))


class SerasaAdapter(SimuladorCredito):
    """Adapter Serasa — valida credenciais; consulta simulada até API real."""

    nome = "serasa"

    def consultar_score(self, *, documento: str, tipo_pessoa: str, credenciais: dict[str, str]):
        if not credenciais.get("api_key") and not credenciais.get("client_id"):
            raise ValueError("Credenciais Serasa ausentes (api_key ou client_id).")
        return super().consultar_score(
            documento=documento, tipo_pessoa=tipo_pessoa, credenciais=credenciais
        )


class SintegraTransitoAdapter(SimuladorTransito):
    """Adapter agregador veicular — valida credenciais; consulta simulada."""

    nome = "sintegra"


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
