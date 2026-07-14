"""Barramento de eventos de domínio (in-process, extensível para Redis Pub/Sub).

Permite que módulos reajam a eventos de outros módulos sem acoplamento direto.
Na Fase 0 os handlers são registrados e executados no mesmo processo; a
interface já está pronta para, no futuro, publicar em filas/Redis e habilitar
o desmembramento em serviços independentes.
"""

from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Evento de domínio base. Módulos definem subclasses específicas."""

    occurred_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Nome estável do evento (usado para roteamento/log)."""
        return self.__class__.__name__


EventHandler = Callable[[DomainEvent], Awaitable[None] | None]


class EventBus:
    """Registro e despacho de handlers de eventos de domínio."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Registra um handler para um tipo de evento."""
        self._handlers[event_type].append(handler)
        logger.debug("Handler %s registrado para %s.", handler.__name__, event_type.__name__)

    async def publish(self, event: DomainEvent) -> None:
        """Despacha um evento para todos os handlers registrados.

        Erros de um handler são logados mas não interrompem os demais, evitando
        que um efeito colateral secundário derrube o fluxo principal.
        """
        handlers = self._handlers.get(type(event), [])
        logger.debug("Publicando evento %s para %d handler(s).", event.name, len(handlers))
        for handler in handlers:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Erro no handler %s do evento %s.", handler.__name__, event.name)


# Instância global do barramento de eventos da aplicação.
event_bus = EventBus()
