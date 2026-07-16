"""Serviço de parâmetros configuráveis (§14.5)."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.audit.service import audit_service
from app.modules.parametros.catalog import (
    CATALOG_BY_KEY,
    CATEGORIA_LABELS,
    PARAM_CATALOG,
    ParamDef,
)
from app.modules.parametros.models import ParametroSistema
from app.modules.parametros.schemas import ParametroValorRead
from app.shared.enums import AuditAction, ParametroCategoria, ParametroTipo


def _serialize_value(valor: Any, tipo: ParametroTipo) -> str:
    if tipo == ParametroTipo.BOOL:
        return "true" if valor in (True, "true", "1", 1, "on", "yes") else "false"
    if tipo == ParametroTipo.JSON:
        return json.dumps(valor, ensure_ascii=False)
    if tipo == ParametroTipo.DECIMAL:
        return str(Decimal(str(valor)))
    return str(valor)


def _parse_value(raw: str, tipo: ParametroTipo) -> Any:
    if tipo == ParametroTipo.INT:
        return int(raw)
    if tipo == ParametroTipo.DECIMAL:
        return Decimal(raw)
    if tipo == ParametroTipo.BOOL:
        return raw.lower() in ("true", "1", "yes", "on")
    if tipo == ParametroTipo.JSON:
        return json.loads(raw)
    return raw


def _validate_value(valor: Any, definition: ParamDef) -> str:
    try:
        serialized = _serialize_value(valor, definition.tipo)
        _parse_value(serialized, definition.tipo)
    except (ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        raise ValidationError(f"Valor inválido para {definition.label}: {exc}") from exc
    if definition.tipo == ParametroTipo.INT and definition.chave == "financeiro.dia_fechamento":
        parsed = int(_parse_value(serialized, definition.tipo))
        if not 1 <= parsed <= 28:
            raise ValidationError("Dia de fechamento deve estar entre 1 e 28.")
    return serialized


class ParametroService:
    """Resolve e persiste parâmetros do tenant/filial."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def get_definition(self, chave: str) -> ParamDef:
        definition = CATALOG_BY_KEY.get(chave)
        if definition is None:
            raise NotFoundError(f"Parâmetro desconhecido: {chave}")
        return definition

    async def _load_overrides(
        self,
        tenant_id: uuid.UUID,
        filial_id: uuid.UUID | None,
    ) -> dict[str, ParametroSistema]:
        stmt = select(ParametroSistema).where(
            ParametroSistema.tenant_id == tenant_id,
            ParametroSistema.deleted_at.is_(None),
        )
        if filial_id is None:
            stmt = stmt.where(ParametroSistema.filial_id.is_(None))
        else:
            stmt = stmt.where(
                ParametroSistema.filial_id.in_([filial_id, None])  # type: ignore[arg-type]
            )
        rows = (await self.session.execute(stmt)).scalars().all()
        tenant_overrides = {r.chave: r for r in rows if r.filial_id is None}
        filial_overrides = {r.chave: r for r in rows if r.filial_id == filial_id}
        merged = dict(tenant_overrides)
        merged.update(filial_overrides)
        return merged

    def _resolve_item(
        self,
        definition: ParamDef,
        overrides: dict[str, ParametroSistema],
        filial_id: uuid.UUID | None,
    ) -> ParametroValorRead:
        row = overrides.get(definition.chave)
        if row is not None:
            valor = _parse_value(row.valor, definition.tipo)
            return ParametroValorRead(
                chave=definition.chave,
                categoria=definition.categoria,
                label=definition.label,
                descricao=definition.descricao,
                tipo=definition.tipo,
                unidade=definition.unidade,
                valor=valor,
                valor_padrao=definition.valor_padrao,
                override=True,
                filial_id=row.filial_id,
            )
        return ParametroValorRead(
            chave=definition.chave,
            categoria=definition.categoria,
            label=definition.label,
            descricao=definition.descricao,
            tipo=definition.tipo,
            unidade=definition.unidade,
            valor=definition.valor_padrao,
            valor_padrao=definition.valor_padrao,
            override=False,
            filial_id=filial_id,
        )

    async def list_resolved(
        self,
        tenant_id: uuid.UUID,
        filial_id: uuid.UUID | None = None,
        categoria: ParametroCategoria | None = None,
    ) -> list[ParametroValorRead]:
        overrides = await self._load_overrides(tenant_id, filial_id)
        items: list[ParametroValorRead] = []
        for definition in PARAM_CATALOG:
            if categoria is not None and definition.categoria != categoria:
                continue
            items.append(self._resolve_item(definition, overrides, filial_id))
        return items

    async def get_valor(
        self,
        chave: str,
        tenant_id: uuid.UUID,
        filial_id: uuid.UUID | None = None,
    ) -> Any:
        definition = self.get_definition(chave)
        overrides = await self._load_overrides(tenant_id, filial_id)
        return self._resolve_item(definition, overrides, filial_id).valor

    async def set_valor(
        self,
        chave: str,
        valor: Any,
        tenant_id: uuid.UUID,
        filial_id: uuid.UUID | None = None,
    ) -> ParametroValorRead:
        definition = self.get_definition(chave)
        serialized = _validate_value(valor, definition)

        stmt = select(ParametroSistema).where(
            ParametroSistema.tenant_id == tenant_id,
            ParametroSistema.chave == chave,
            ParametroSistema.deleted_at.is_(None),
        )
        if filial_id is None:
            stmt = stmt.where(ParametroSistema.filial_id.is_(None))
        else:
            stmt = stmt.where(ParametroSistema.filial_id == filial_id)

        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = ParametroSistema(
                tenant_id=tenant_id,
                filial_id=filial_id,
                chave=chave,
                valor=serialized,
            )
            self.session.add(row)
        else:
            row.valor = serialized

        await audit_service.record(
            AuditAction.UPDATE,
            entity="parametro_sistema",
            entity_id=row.id,
            description=f"Parâmetro {chave} atualizado",
            changes={"chave": chave, "filial_id": str(filial_id) if filial_id else None},
        )
        overrides = {chave: row}
        return self._resolve_item(definition, overrides, filial_id)

    async def reset_valor(
        self,
        chave: str,
        tenant_id: uuid.UUID,
        filial_id: uuid.UUID | None = None,
    ) -> ParametroValorRead:
        definition = self.get_definition(chave)
        stmt = select(ParametroSistema).where(
            ParametroSistema.tenant_id == tenant_id,
            ParametroSistema.chave == chave,
            ParametroSistema.deleted_at.is_(None),
        )
        if filial_id is None:
            stmt = stmt.where(ParametroSistema.filial_id.is_(None))
        else:
            stmt = stmt.where(ParametroSistema.filial_id == filial_id)

        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is not None:
            from datetime import UTC, datetime

            row.deleted_at = datetime.now(UTC)
            await audit_service.record(
                AuditAction.DELETE,
                entity="parametro_sistema",
                entity_id=row.id,
                description=f"Parâmetro {chave} restaurado ao padrão",
            )
        return ParametroValorRead(
            chave=definition.chave,
            categoria=definition.categoria,
            label=definition.label,
            descricao=definition.descricao,
            tipo=definition.tipo,
            unidade=definition.unidade,
            valor=definition.valor_padrao,
            valor_padrao=definition.valor_padrao,
            override=False,
            filial_id=filial_id,
        )

    def list_categorias(self) -> list[tuple[ParametroCategoria, str]]:
        seen: list[ParametroCategoria] = []
        for definition in PARAM_CATALOG:
            if definition.categoria not in seen:
                seen.append(definition.categoria)
        return [(cat, CATEGORIA_LABELS[cat]) for cat in seen]

    async def bulk_update(
        self,
        valores: dict[str, Any],
        tenant_id: uuid.UUID,
        filial_id: uuid.UUID | None = None,
    ) -> list[ParametroValorRead]:
        results: list[ParametroValorRead] = []
        for chave, valor in valores.items():
            results.append(await self.set_valor(chave, valor, tenant_id, filial_id))
        return results
