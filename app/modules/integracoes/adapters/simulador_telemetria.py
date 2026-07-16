"""Simulador de provedor de telemetria (§12.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.modules.integracoes.adapters.telemetria_port import (
    TelemetriaEventoExterno,
    TelemetriaPosicao,
)


class SimuladorTelemetria:
    nome = "simulador"

    def sincronizar(
        self, *, credenciais: dict[str, str], equipamentos: list[str]
    ) -> tuple[list[TelemetriaPosicao], list[TelemetriaEventoExterno]]:
        _ = credenciais
        now = datetime.now(tz=UTC)
        posicoes: list[TelemetriaPosicao] = []
        eventos: list[TelemetriaEventoExterno] = []
        for idx, eq in enumerate(equipamentos or ["SIM-001"]):
            posicoes.append(
                TelemetriaPosicao(
                    equipamento_id=eq,
                    lat=Decimal("-23.5505") + Decimal(idx) * Decimal("0.001"),
                    lng=Decimal("-46.6333") + Decimal(idx) * Decimal("0.001"),
                    km=10000 + idx * 50,
                    conn_status="online",
                    atualizado_em=now,
                )
            )
            eventos.append(
                TelemetriaEventoExterno(
                    equipamento_id=eq,
                    tipo="geofence",
                    descricao="Entrada em área monitorada (simulado)",
                    lat=posicoes[-1].lat,
                    lng=posicoes[-1].lng,
                    velocidade=Decimal("45"),
                    ocorrido_em=now,
                    payload={"simulado": True},
                )
            )
        return posicoes, eventos
