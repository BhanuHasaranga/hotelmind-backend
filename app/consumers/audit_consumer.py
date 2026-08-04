from app.consumers.base import BaseConsumer
from app.events.topics import ALL_TOPICS
from app.handlers.audit_handlers import handle_audit_event


class AuditConsumer(BaseConsumer):
    name = "audit-consumer"
    topics = [t for t in ALL_TOPICS if t not in ("audit.events",)]

    async def handle(self, event: dict) -> None:
        await handle_audit_event(self._redis, event)
