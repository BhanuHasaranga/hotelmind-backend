import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_NOTIFIABLE_EVENT_TYPES = {
    "ReservationCreated",
    "ReservationConfirmed",
    "ReservationCancelled",
    "PaymentCompleted",
    "RefundIssued",
    "ReviewCreated",
}


async def handle_notification_event(redis: Redis, event: dict) -> None:
    """Placeholder notification dispatch - logs a structured notification record.
    A real implementation would push to email/SMS/push providers; kept minimal
    for Phase 7 scope while still exercising the full consumer pipeline.
    """
    event_type = event.get("event_type")
    if event_type not in _NOTIFIABLE_EVENT_TYPES:
        return
    logger.info(
        "Notification dispatched",
        extra={"event_type": event_type, "aggregate_id": event.get("aggregate_id")},
    )
