"""Simulador de bureau de crédito (§12.3)."""

from __future__ import annotations

from app.modules.integracoes.adapters.credito_port import CreditoConsultaResultado


class SimuladorCredito:
    nome = "simulador"

    def consultar_score(
        self, *, documento: str, tipo_pessoa: str, credenciais: dict[str, str]
    ) -> CreditoConsultaResultado:
        _ = credenciais
        digits = "".join(c for c in documento if c.isdigit())
        score = 300 + (sum(int(d) for d in digits[-6:]) * 7) % 550
        restricao = score < 400
        return CreditoConsultaResultado(
            score=min(score, 900),
            restricao=restricao,
            motivo="Score abaixo do mínimo" if restricao else None,
            bureau=f"simulador-{tipo_pessoa}",
        )
