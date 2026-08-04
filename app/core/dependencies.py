from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import settings
from app.producers.base import EventPublisher

_redis_client: Redis | None = None


def get_event_publisher(request: Request) -> EventPublisher:
    return request.app.state.event_publisher


async def get_redis() -> AsyncGenerator[Redis, None]:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield _redis_client
