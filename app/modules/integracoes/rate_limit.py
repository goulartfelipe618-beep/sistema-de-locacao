"""Rate limiting da API pública via Redis (§12.5)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.cache import redis_client
from app.core.exceptions import ValidationError


async def enforce_api_key_rate_limit(key_prefix: str, limit_per_minute: int) -> None:
    """Incrementa contador por minuto e bloqueia quando exceder o limite da chave."""
    if limit_per_minute <= 0:
        return
    window = datetime.now(tz=UTC).strftime("%Y%m%d%H%M")
    redis_key = f"ratelimit:apikey:{key_prefix}:{window}"
    count = await redis_client.incr(redis_key)
    if count == 1:
        await redis_client.expire(redis_key, 65)
    if count > limit_per_minute:
        raise ValidationError(
            f"Rate limit excedido ({limit_per_minute} req/min). Tente novamente em instantes.",
            code="rate_limit_exceeded",
        )
