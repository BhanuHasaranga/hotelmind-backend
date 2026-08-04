from app.consumers.base import BaseConsumer
from app.events.topics import RESTAURANT_EVENTS
from app.handlers.restaurant_handlers import handle_restaurant_event


class RestaurantConsumer(BaseConsumer):
    name = "restaurant-consumer"
    topics = [RESTAURANT_EVENTS]

    async def handle(self, event: dict) -> None:
        await handle_restaurant_event(self._redis, event)
