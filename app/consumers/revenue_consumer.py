from app.consumers.base import BaseConsumer
from app.events.topics import BOOKING_EVENTS, PAYMENT_EVENTS
from app.handlers.revenue_handlers import handle_revenue_event


class RevenueConsumer(BaseConsumer):
    name = "revenue-consumer"
    topics = [BOOKING_EVENTS, PAYMENT_EVENTS]

    async def handle(self, event: dict) -> None:
        await handle_revenue_event(self._redis, event)
