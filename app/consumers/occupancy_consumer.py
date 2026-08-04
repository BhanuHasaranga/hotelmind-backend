from app.consumers.base import BaseConsumer
from app.events.topics import BOOKING_EVENTS
from app.handlers.occupancy_handlers import handle_occupancy_event


class OccupancyConsumer(BaseConsumer):
    name = "occupancy-consumer"
    topics = [BOOKING_EVENTS]

    async def handle(self, event: dict) -> None:
        await handle_occupancy_event(self._redis, event)
