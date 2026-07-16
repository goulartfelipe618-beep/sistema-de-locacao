"""Cache Redis dos KPIs materializados do Dashboard (§1)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.cache import cache_get_json, cache_set_json


def kpi_cache_key(tenant_id: uuid.UUID, filial_id: uuid.UUID | None) -> str:
    filial_part = str(filial_id) if filial_id else "all"
    return f"dashboard:kpis:{tenant_id}:{filial_part}"


def encode_snapshot(snap: Any) -> dict[str, Any]:
    """Serializa DashboardSnapshot (dataclass) para JSON."""

    def _encode(value: Any) -> Any:
        if is_dataclass(value):
            return {f.name: _encode(getattr(value, f.name)) for f in fields(value)}
        if isinstance(value, list):
            return [_encode(item) for item in value]
        if isinstance(value, dict):
            return {k: _encode(v) for k, v in value.items()}
        if isinstance(value, Decimal):
            return str(value)
        return value

    return _encode(snap)


def decode_snapshot_dict(data: dict[str, Any], snapshot_cls: type) -> Any:
    """Reconstrói DashboardSnapshot a partir de dict."""
    from app.modules.dashboard.service import (
        AlertaItem,
        DashboardSnapshot,
        FinanceiroKpis,
        FrotaKpis,
        LocacoesKpis,
        ManutencaoKpis,
        OcupacaoPonto,
        ReservasKpis,
    )

    snap = snapshot_cls(
        total_users=int(data.get("total_users", 0)),
        active_users=int(data.get("active_users", 0)),
        total_filiais=int(data.get("total_filiais", 0)),
        active_filiais=int(data.get("active_filiais", 0)),
    )
    if data.get("frota"):
        snap.frota = FrotaKpis(**data["frota"])
    if data.get("reservas"):
        snap.reservas = ReservasKpis(**data["reservas"])
    if data.get("locacoes"):
        snap.locacoes = LocacoesKpis(**data["locacoes"])
    if data.get("financeiro"):
        fin = dict(data["financeiro"])
        for key in (
            "faturamento_dia",
            "faturamento_mes",
            "receber_aberto",
            "receber_vencido",
            "pagar_aberto",
            "pagar_vencido",
            "saldo_caixa",
        ):
            if key in fin and fin[key] is not None:
                fin[key] = Decimal(str(fin[key]))
        snap.financeiro = FinanceiroKpis(**fin)
    if data.get("manutencao"):
        snap.manutencao = ManutencaoKpis(**data["manutencao"])
    if data.get("comercial"):
        snap.comercial = ComercialKpis(**data["comercial"])
    snap.ocupacao_30 = [OcupacaoPonto(**p) for p in data.get("ocupacao_30", [])]
    snap.ocupacao_90 = [OcupacaoPonto(**p) for p in data.get("ocupacao_90", [])]
    snap.alertas = [AlertaItem(**a) for a in data.get("alertas", [])]
    return snap


async def load_snapshot_cache(
    tenant_id: uuid.UUID,
    filial_id: uuid.UUID | None,
    *,
    snapshot_cls: type,
) -> tuple[Any, datetime] | None:
    payload = await cache_get_json(kpi_cache_key(tenant_id, filial_id))
    if not payload or "snapshot" not in payload:
        return None
    materialized_at = datetime.fromisoformat(payload["materialized_at"])
    return decode_snapshot_dict(payload["snapshot"], snapshot_cls), materialized_at


async def save_snapshot_cache(
    tenant_id: uuid.UUID,
    filial_id: uuid.UUID | None,
    snap: Any,
    *,
    ttl_seconds: int,
) -> datetime:
    materialized_at = datetime.now(UTC)
    payload = {
        "materialized_at": materialized_at.isoformat(),
        "snapshot": encode_snapshot(snap),
    }
    await cache_set_json(
        kpi_cache_key(tenant_id, filial_id),
        payload,
        ttl_seconds=ttl_seconds,
    )
    return materialized_at


def snapshot_asdict(snap: Any) -> dict[str, Any]:
    return asdict(snap)
