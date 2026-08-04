import logging
from decimal import Decimal

from redis.asyncio import Redis

from app.redis_cache.dashboard_cache import get_restaurant_sales, publish_dashboard_update, set_restaurant_sales

logger = logging.getLogger(__name__)

_SALES_EVENT_TYPES = {"OrderCompleted"}


async def handle_restaurant_event(redis: Redis, event: dict) -> None:
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    branch_id = payload.get("branch_id", "global")

    if event_type in _SALES_EVENT_TYPES:
        amount = Decimal(str(payload.get("total_amount") or "0"))
        current = await get_restaurant_sales(redis, branch_id) or Decimal("0")
        new_total = current + amount
        await set_restaurant_sales(redis, branch_id, new_total)

    await publish_dashboard_update(redis, {"type": "restaurant", "event_type": event_type, "payload": payload})
