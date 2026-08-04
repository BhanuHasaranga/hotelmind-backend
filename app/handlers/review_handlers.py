import json
import logging

from redis.asyncio import Redis

from app.redis_cache.dashboard_cache import publish_dashboard_update
from app.redis_cache.keys import review_sentiment_key

logger = logging.getLogger(__name__)

_TRACKED_EVENT_TYPES = {"ReviewCreated", "SentimentCalculated"}


async def handle_review_event(redis: Redis, event: dict) -> None:
    """Consumes review.events so ReviewCreated/SentimentCalculated reach the
    dashboard read-model and WebSocket clients, mirroring how BookingConsumer
    and RestaurantConsumer bridge their domain events to dashboard:updates.
    """
    event_type = event.get("event_type")
    if event_type not in _TRACKED_EVENT_TYPES:
        return

    payload = event.get("payload", {})

    if event_type == "SentimentCalculated":
        review_id = str(payload.get("review_id"))
        await redis.set(review_sentiment_key(review_id), json.dumps(payload, default=str), ex=86400)

    await publish_dashboard_update(redis, {"type": "review", "event_type": event_type, "payload": payload})
