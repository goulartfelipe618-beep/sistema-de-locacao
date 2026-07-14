"""Cliente Redis assíncrono para cache, locks e dados efêmeros.

Fornece um cliente único (pool interno) e utilitários de alto nível como
cache com serialização JSON e locks distribuídos.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio.client import Redis
from redis.asyncio.lock import Lock

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cliente Redis único da aplicação (thread/async-safe, com pool interno).
redis_client: Redis = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    health_check_interval=30,
)


async def cache_get_json(key: str) -> Any | None:
    """Recupera e desserializa um valor JSON do cache."""
    raw = await redis_client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Valor não-JSON no cache para a chave %s.", key)
        return None


async def cache_set_json(key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
    """Serializa e armazena um valor JSON no cache com TTL opcional."""
    payload = json.dumps(value, ensure_ascii=False, default=str)
    await redis_client.set(key, payload, ex=ttl_seconds)


async def cache_delete(*keys: str) -> None:
    """Remove uma ou mais chaves do cache."""
    if keys:
        await redis_client.delete(*keys)


@asynccontextmanager
async def distributed_lock(
    name: str,
    *,
    timeout: float = 30.0,
    blocking_timeout: float = 10.0,
) -> AsyncIterator[Lock]:
    """Adquire um lock distribuído (evita processamento concorrente indevido)."""
    lock = redis_client.lock(f"lock:{name}", timeout=timeout, blocking_timeout=blocking_timeout)
    acquired = await lock.acquire()
    if not acquired:
        raise TimeoutError(f"Não foi possível adquirir o lock: {name}")
    try:
        yield lock
    finally:
        try:
            await lock.release()
        except Exception:  # pragma: no cover - lock pode ter expirado
            logger.debug("Lock %s já expirado ao liberar.", name)


async def check_redis() -> bool:
    """Verifica a conectividade com o Redis (health check de readiness)."""
    try:
        return bool(await redis_client.ping())
    except Exception as exc:  # pragma: no cover - depende de infraestrutura
        logger.warning("Health check do Redis falhou: %s", exc)
        return False


async def close_redis() -> None:
    """Encerra as conexões do Redis (shutdown da aplicação)."""
    await redis_client.aclose()
