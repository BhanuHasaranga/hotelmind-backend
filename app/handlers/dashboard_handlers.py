import logging

from redis.asyncio import Redis

from app.redis_cache.dashboard_cache import publish_dashboard_update

logger = logging.getLogger(__name__)


async def handle_dashboard_event(redis: Redis, event: dict) -> None:
    """Consumes dashboard.events (published by upstream aggregation/ML jobs) and
    fans them out to WebSocket clients via Redis Pub/Sub. This is the consumer
    that the API process's pubsub bridge relies on for live updates.
    """
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    await publish_dashboard_update(redis, {"type": "dashboard", "event_type": event_type, "payload": payload})
