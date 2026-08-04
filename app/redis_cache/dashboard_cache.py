import json
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis

from app.metrics.prometheus import redis_cache_hits, redis_cache_misses
from app.redis_cache import keys

_CACHE_TTL_SECONDS = 300


async def get_summary(redis: Redis, branch_id: str) -> dict[str, Any] | None:
    raw = await redis.get(keys.summary_key(branch_id))
    if raw is None:
        redis_cache_misses.labels(key_prefix="dashboard:summary").inc()
        return None
    redis_cache_hits.labels(key_prefix="dashboard:summary").inc()
    return json.loads(raw)


async def set_summary(redis: Redis, branch_id: str, summary: dict[str, Any]) -> None:
    await redis.set(keys.summary_key(branch_id), json.dumps(summary, default=str), ex=_CACHE_TTL_SECONDS)


async def get_occupancy(redis: Redis, branch_id: str) -> float | None:
    raw = await redis.get(keys.occupancy_key(branch_id))
    if raw is None:
        redis_cache_misses.labels(key_prefix="dashboard:occupancy").inc()
        return None
    redis_cache_hits.labels(key_prefix="dashboard:occupancy").inc()
    return float(raw)


async def set_occupancy(redis: Redis, branch_id: str, occupancy_pct: float) -> None:
    await redis.set(keys.occupancy_key(branch_id), str(occupancy_pct), ex=_CACHE_TTL_SECONDS)


async def get_revenue(redis: Redis, branch_id: str) -> Decimal | None:
    raw = await redis.get(keys.revenue_key(branch_id))
    if raw is None:
        redis_cache_misses.labels(key_prefix="dashboard:revenue").inc()
        return None
    redis_cache_hits.labels(key_prefix="dashboard:revenue").inc()
    return Decimal(raw)


async def set_revenue(redis: Redis, branch_id: str, revenue: Decimal) -> None:
    await redis.set(keys.revenue_key(branch_id), str(revenue), ex=_CACHE_TTL_SECONDS)


async def get_booking_count(redis: Redis, branch_id: str) -> int | None:
    raw = await redis.get(keys.booking_count_key(branch_id))
    if raw is None:
        redis_cache_misses.labels(key_prefix="dashboard:booking_count").inc()
        return None
    redis_cache_hits.labels(key_prefix="dashboard:booking_count").inc()
    return int(raw)


async def set_booking_count(redis: Redis, branch_id: str, count: int) -> None:
    await redis.set(keys.booking_count_key(branch_id), str(count), ex=_CACHE_TTL_SECONDS)


async def get_restaurant_sales(redis: Redis, branch_id: str) -> Decimal | None:
    raw = await redis.get(keys.restaurant_sales_key(branch_id))
    if raw is None:
        redis_cache_misses.labels(key_prefix="dashboard:restaurant_sales").inc()
        return None
    redis_cache_hits.labels(key_prefix="dashboard:restaurant_sales").inc()
    return Decimal(raw)


async def set_restaurant_sales(redis: Redis, branch_id: str, sales: Decimal) -> None:
    await redis.set(keys.restaurant_sales_key(branch_id), str(sales), ex=_CACHE_TTL_SECONDS)


async def publish_dashboard_update(redis: Redis, payload: dict[str, Any]) -> None:
    await redis.publish(keys.DASHBOARD_UPDATES_CHANNEL, json.dumps(payload, default=str))


async def mark_event_seen(redis: Redis, consumer_name: str, event_id: str, ttl_seconds: int = 86400) -> bool:
    """Returns True if this is the first time this consumer has seen event_id (SETNX semantics).

    Idempotency is scoped per-consumer: the same event_id is legitimately processed once by
    each independent consumer group (booking-consumer, audit-consumer, etc.), so the dedupe
    key must not be shared globally across consumers.
    """
    return bool(await redis.set(keys.event_seen_key(consumer_name, event_id), "1", nx=True, ex=ttl_seconds))
