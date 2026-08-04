from app.consumers.base import BaseConsumer
from app.events.topics import BOOKING_EVENTS, PAYMENT_EVENTS, REVIEW_EVENTS
from app.handlers.notification_handlers import handle_notification_event


class NotificationConsumer(BaseConsumer):
    name = "notification-consumer"
    topics = [BOOKING_EVENTS, PAYMENT_EVENTS, REVIEW_EVENTS]

    async def handle(self, event: dict) -> None:
        await handle_notification_event(self._redis, event)
