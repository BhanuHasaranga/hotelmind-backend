import logging
from decimal import Decimal

from redis.asyncio import Redis

from app.redis_cache.dashboard_cache import get_revenue, publish_dashboard_update, set_revenue

logger = logging.getLogger(__name__)

_REVENUE_EVENT_TYPES = {"ReservationCreated", "ReservationCancelled", "PaymentCompleted", "RefundIssued"}


async def handle_revenue_event(redis: Redis, event: dict) -> None:
    event_type = event.get("event_type")
    if event_type not in _REVENUE_EVENT_TYPES:
        return

    payload = event.get("payload", {})
    branch_id = payload.get("branch_id", "global")
    amount = Decimal(str(payload.get("total_amount") or payload.get("amount") or "0"))

    current = await get_revenue(redis, branch_id) or Decimal("0")
    if event_type in ("ReservationCreated", "PaymentCompleted"):
        new_total = current + amount
    else:
        new_total = current - amount
    await set_revenue(redis, branch_id, max(new_total, Decimal("0")))

    await publish_dashboard_update(
        redis, {"type": "revenue", "event_type": event_type, "branch_id": branch_id, "total_revenue": str(max(new_total, Decimal("0")))}
    )
