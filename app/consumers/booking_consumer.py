from app.consumers.base import BaseConsumer
from app.events.topics import BOOKING_EVENTS
from app.handlers.booking_handlers import handle_booking_event


class BookingConsumer(BaseConsumer):
    name = "booking-consumer"
    topics = [BOOKING_EVENTS]

    async def handle(self, event: dict) -> None:
        await handle_booking_event(self._redis, event)
