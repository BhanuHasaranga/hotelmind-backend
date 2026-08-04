import asyncio
import threading
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.events.schemas import BaseEvent, ReservationCreated
from app.events.topics import BOOKING_EVENTS
from app.handlers.booking_handlers import handle_booking_event
from app.producers.base import EventPublisher
from app.websocket.router import manager
from app.websocket.router import router as websocket_router


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.published: list[tuple[str, str]] = []

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def publish(self, channel: str, message: str):
        self.published.append((channel, message))


class FakePublisher(EventPublisher):
    def __init__(self) -> None:
        self.published: list[tuple[BaseEvent, str]] = []

    async def publish(self, event: BaseEvent, topic: str) -> None:
        self.published.append((event, topic))


@pytest.mark.asyncio
async def test_booking_created_flows_through_redis_and_pubsub():
    """End-to-end (without real Kafka): a service publishes a ReservationCreated
    event via a fake publisher, the pure booking handler consumes it and writes
    to Redis + publishes on the dashboard:updates channel, mimicking what the
    real BookingConsumer/DashboardConsumer pair does.
    """
    redis = FakeRedis()
    branch_id = str(uuid.uuid4())

    event = BaseEvent(
        event_type="ReservationCreated",
        aggregate_type="Reservation",
        aggregate_id=str(uuid.uuid4()),
        payload=ReservationCreated(
            reservation_id=uuid.uuid4(),
            room_id=uuid.uuid4(),
            guest_id=uuid.uuid4(),
            check_in_date="2026-01-01",
            check_out_date="2026-01-05",
            status="PENDING",
            total_amount="200.00",
        ).model_dump(mode="json"),
    )
    event.payload["branch_id"] = branch_id

    publisher = FakePublisher()
    await publisher.publish(event, BOOKING_EVENTS)
    assert publisher.published[0][1] == BOOKING_EVENTS

    await handle_booking_event(redis, event.model_dump(mode="json"))

    assert redis.store[f"dashboard:booking_count:{branch_id}"] == "1"
    assert len(redis.published) == 1
    channel, message = redis.published[0]
    assert channel == "dashboard:updates"
    assert "ReservationCreated" in message


def test_websocket_receives_dashboard_update_end_to_end():
    app = FastAPI()
    app.include_router(websocket_router)
    client = TestClient(app)

    token = create_access_token(subject=uuid.uuid4(), role="OWNER", branch_id=None)

    with client.websocket_connect(f"/ws/dashboard?token={token}") as websocket:
        def _broadcast():
            asyncio.run(manager.broadcast({"type": "booking", "event_type": "ReservationCreated"}))

        t = threading.Thread(target=_broadcast)
        t.start()
        t.join()

        message = websocket.receive_json()
        assert message["event_type"] == "ReservationCreated"
