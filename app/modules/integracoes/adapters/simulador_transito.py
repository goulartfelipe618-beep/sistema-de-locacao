"""Simulador de consultas DETRAN/trânsito (§12.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.modules.integracoes.adapters.transito_port import (
    CnhConsulta,
    DebitoVeicular,
    MultaTransito,
)


class SimuladorTransito:
    nome = "simulador"

    def consultar_multas_veiculo(
        self, *, placa: str, renavam: str | None, credenciais: dict[str, str]
    ) -> list[MultaTransito]:
        _ = renavam, credenciais
        placa = placa.upper()
        return [
            MultaTransito(
                ait=f"SIM-{placa[-4:]}-001",
                codigo_infracao="7455-0",
                orgao="DETRAN-SIM",
                valor=Decimal("195.23"),
                pontuacao=5,
                ocorrido_em=datetime.now(tz=UTC) - timedelta(days=12),
            )
        ]

    def consultar_cnh(
        self, *, cnh_numero: str, cpf: str | None, credenciais: dict[str, str]
    ) -> CnhConsulta:
        _ = cpf, credenciais
        return CnhConsulta(
            numero=cnh_numero,
            categoria="B",
            validade=datetime.now(tz=UTC) + timedelta(days=400),
            pontuacao=3,
            status="regular",
        )

    def consultar_debitos_veiculo(
        self, *, placa: str, renavam: str | None, credenciais: dict[str, str]
    ) -> list[DebitoVeicular]:
        _ = renavam, credenciais
        return [
            DebitoVeicular(
                tipo="IPVA",
                descricao=f"IPVA {placa.upper()}",
                valor=Decimal("850.00"),
                vencimento=datetime.now(tz=UTC) + timedelta(days=90),
            )
        ]
