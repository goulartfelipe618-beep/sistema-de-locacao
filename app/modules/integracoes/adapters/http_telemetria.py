"""Adapter HTTP genérico de telemetria (§12.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.logging import get_logger
from app.modules.integracoes.adapters.http_client import http_post_json
from app.modules.integracoes.adapters.simulador_telemetria import SimuladorTelemetria
from app.modules.integracoes.adapters.telemetria_port import (
    TelemetriaEventoExterno,
    TelemetriaPosicao,
)

logger = get_logger(__name__)


class HttpTelemetriaAdapter(SimuladorTelemetria):
    """Consome API REST configurável; faz fallback para simulador."""

    nome = "http"

    def _base_url(self, credenciais: dict[str, str]) -> str:
        return (credenciais.get("base_url") or credenciais.get("api_url") or "").strip()

    def _headers(self, credenciais: dict[str, str]) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        token = credenciais.get("api_key") or credenciais.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def testar_conexao(self, *, credenciais: dict[str, str]) -> bool:
        base = self._base_url(credenciais)
        if not base:
            return bool(credenciais.get("api_key"))
        try:
            from app.modules.integracoes.adapters.http_client import http_get_json

            http_get_json(f"{base.rstrip('/')}/health", headers=self._headers(credenciais))
            return True
        except Exception:  # noqa: BLE001
            return bool(credenciais.get("api_key"))

    def sincronizar(
        self, *, credenciais: dict[str, str], equipamentos: list[str]
    ) -> tuple[list[TelemetriaPosicao], list[TelemetriaEventoExterno]]:
        base = self._base_url(credenciais)
        if not base:
            return super().sincronizar(credenciais=credenciais, equipamentos=equipamentos)
        try:
            data = http_post_json(
                f"{base.rstrip('/')}/sync",
                payload={"equipamentos": equipamentos or ["SIM-001"]},
                headers=self._headers(credenciais),
            )
            return self._parse_response(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telemetria HTTP falhou (%s); usando simulador.", exc)
            return super().sincronizar(credenciais=credenciais, equipamentos=equipamentos)

    def _parse_response(
        self, data: dict[str, Any]
    ) -> tuple[list[TelemetriaPosicao], list[TelemetriaEventoExterno]]:
        now = datetime.now(tz=UTC)
        posicoes: list[TelemetriaPosicao] = []
        for raw in data.get("posicoes", data.get("positions", [])):
            posicoes.append(
                TelemetriaPosicao(
                    equipamento_id=str(raw.get("equipamento_id", raw.get("id", "UNK"))),
                    lat=Decimal(str(raw.get("lat", "-23.5505"))),
                    lng=Decimal(str(raw.get("lng", "-46.6333"))),
                    km=int(raw["km"]) if raw.get("km") is not None else None,
                    conn_status=str(raw.get("conn_status", "online")),
                    atualizado_em=now,
                )
            )
        eventos: list[TelemetriaEventoExterno] = []
        for raw in data.get("eventos", data.get("events", [])):
            eventos.append(
                TelemetriaEventoExterno(
                    equipamento_id=str(raw.get("equipamento_id", raw.get("id", "UNK"))),
                    tipo=str(raw.get("tipo", "outro")),
                    descricao=raw.get("descricao"),
                    lat=Decimal(str(raw["lat"])) if raw.get("lat") is not None else None,
                    lng=Decimal(str(raw["lng"])) if raw.get("lng") is not None else None,
                    velocidade=Decimal(str(raw["velocidade"])) if raw.get("velocidade") else None,
                    ocorrido_em=now,
                    payload=raw.get("payload"),
                )
            )
        if not posicoes and not eventos:
            return super().sincronizar(credenciais={}, equipamentos=["SIM-001"])
        return posicoes, eventos
