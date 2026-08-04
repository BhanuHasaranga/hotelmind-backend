import logging

from redis.asyncio import Redis

from app.redis_cache.dashboard_cache import publish_dashboard_update, set_occupancy

logger = logging.getLogger(__name__)

_OCCUPANCY_EVENT_TYPES = {"ReservationCheckedIn", "ReservationCheckedOut"}


async def handle_occupancy_event(redis: Redis, event: dict) -> None:
    event_type = event.get("event_type")
    if event_type not in _OCCUPANCY_EVENT_TYPES:
        return

    payload = event.get("payload", {})
    branch_id = payload.get("branch_id", "global")

    # Real occupancy_pct is recomputed by the ML/dashboard pipeline from Postgres;
    # here we simply signal that occupancy changed so downstream consumers/dashboards refresh.
    await publish_dashboard_update(
        redis, {"type": "occupancy", "event_type": event_type, "branch_id": branch_id, "room_id": payload.get("room_id")}
    )


async def set_occupancy_pct(redis: Redis, branch_id: str, occupancy_pct: float) -> None:
    await set_occupancy(redis, branch_id, occupancy_pct)
    await publish_dashboard_update(
        redis, {"type": "occupancy_changed", "branch_id": branch_id, "occupancy_pct": occupancy_pct}
    )
