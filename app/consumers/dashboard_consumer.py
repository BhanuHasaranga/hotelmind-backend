from app.consumers.base import BaseConsumer
from app.events.topics import DASHBOARD_EVENTS
from app.handlers.dashboard_handlers import handle_dashboard_event


class DashboardConsumer(BaseConsumer):
    name = "dashboard-consumer"
    topics = [DASHBOARD_EVENTS]

    async def handle(self, event: dict) -> None:
        await handle_dashboard_event(self._redis, event)
