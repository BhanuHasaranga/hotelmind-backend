import logging

from redis.asyncio import Redis

from app.redis_cache.dashboard_cache import get_booking_count, publish_dashboard_update, set_booking_count

logger = logging.getLogger(__name__)

_TRACKED_EVENT_TYPES = {
    "ReservationCreated",
    "ReservationConfirmed",
    "ReservationCancelled",
    "ReservationCheckedIn",
    "ReservationCheckedOut",
    "ReservationUpdated",
}


async def handle_booking_event(redis: Redis, event: dict) -> None:
    event_type = event.get("event_type")
    if event_type not in _TRACKED_EVENT_TYPES:
        return

    payload = event.get("payload", {})
    branch_id = payload.get("branch_id", "global")

    if event_type == "ReservationCreated":
        current = await get_booking_count(redis, branch_id) or 0
        await set_booking_count(redis, branch_id, current + 1)
    elif event_type == "ReservationCancelled":
        current = await get_booking_count(redis, branch_id) or 0
        await set_booking_count(redis, branch_id, max(current - 1, 0))

    await publish_dashboard_update(redis, {"type": "booking", "event_type": event_type, "payload": payload})
