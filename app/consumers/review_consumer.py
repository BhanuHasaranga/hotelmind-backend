from app.consumers.base import BaseConsumer
from app.events.topics import REVIEW_EVENTS
from app.handlers.review_handlers import handle_review_event


class ReviewConsumer(BaseConsumer):
    name = "review-consumer"
    topics = [REVIEW_EVENTS]

    async def handle(self, event: dict) -> None:
        await handle_review_event(self._redis, event)
