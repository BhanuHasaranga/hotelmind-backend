import json
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def handle_audit_event(redis: Redis, event: dict) -> None:
    """Appends every event to an append-only audit log in Redis (capped list)
    for lightweight traceability. A production system would sink this to
    durable storage (e.g. an audit table or object storage) instead.
    """
    await redis.lpush("audit:log", json.dumps(event, default=str))
    await redis.ltrim("audit:log", 0, 9999)
    logger.info("Audit event recorded", extra={"event_type": event.get("event_type")})
