"""
Redis connection & dynamic per-company rate limiter.

Uses a sliding-window counter in Redis keyed by company_id.
Gracefully degrades (no limiting) if Redis is unavailable.
"""

from __future__ import annotations

import logging
import time

import redis.asyncio as redis
from fastapi import HTTPException, Request

from app.core.config import get_settings

logger = logging.getLogger("wasla.rate_limit")

# ── Module-level connection (set during app lifespan) ─────────────
_redis: redis.Redis | None = None


async def init_redis() -> None:
    """Open the Redis connection pool. Called from the app lifespan."""
    global _redis
    settings = get_settings()
    try:
        _redis = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        await _redis.ping()
        logger.info("Redis connected at %s", settings.redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — rate limiting disabled", exc)
        _redis = None


async def close_redis() -> None:
    """Close the pool. Called from the app lifespan."""
    global _redis
    if _redis is not None:
        await _redis.aclose()  # type: ignore[union-attr]
        _redis = None
        logger.info("Redis connection closed")


async def check_rate_limit(company_id: str) -> None:
    """
    Sliding-window rate limiter keyed by ``company_id``.

    Raises ``HTTPException(429)`` if the company has exceeded
    ``rate_limit_requests`` within ``rate_limit_window_seconds``.
    Does nothing if Redis is not connected.
    """
    if _redis is None:
        return  # gracefully skip if Redis is down

    settings = get_settings()
    key = f"rate:{company_id}"
    now = time.time()
    window = settings.rate_limit_window_seconds

    pipe = _redis.pipeline()
    pipe.zremrangebyscore(key, "-inf", now - window)  # prune old entries
    pipe.zadd(key, {str(now): now})                   # record this request
    pipe.zcard(key)                                    # count in window
    pipe.expire(key, window)                           # auto-cleanup
    results = await pipe.execute()

    request_count = results[2]

    if request_count > settings.rate_limit_requests:
        logger.warning(
            "Rate limit exceeded for company %s (%d/%d in %ds)",
            company_id,
            request_count,
            settings.rate_limit_requests,
            window,
        )
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded: {settings.rate_limit_requests} "
                f"requests per {window}s. Please try again shortly."
            ),
        )
