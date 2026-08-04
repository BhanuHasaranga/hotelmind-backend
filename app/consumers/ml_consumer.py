from app.consumers.base import BaseConsumer
from app.events.topics import ML_PREDICTIONS
from app.handlers.ml_handlers import handle_ml_event


class MLConsumer(BaseConsumer):
    name = "ml-consumer"
    topics = [ML_PREDICTIONS]

    async def handle(self, event: dict) -> None:
        await handle_ml_event(self._redis, event)
