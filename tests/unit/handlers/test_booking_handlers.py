import pytest

from app.handlers.booking_handlers import handle_booking_event
from app.redis_cache.keys import booking_count_key


@pytest.mark.asyncio
async def test_reservation_created_increments_booking_count(fake_redis):
    event = {
        "event_type": "ReservationCreated",
        "payload": {"branch_id": "b1", "reservation_id": "r1"},
    }
    await handle_booking_event(fake_redis, event)
    assert fake_redis.store[booking_count_key("b1")] == "1"
    assert len(fake_redis.published) == 1


@pytest.mark.asyncio
async def test_reservation_cancelled_decrements_booking_count(fake_redis):
    fake_redis.store[booking_count_key("b1")] = "3"
    event = {"event_type": "ReservationCancelled", "payload": {"branch_id": "b1"}}
    await handle_booking_event(fake_redis, event)
    assert fake_redis.store[booking_count_key("b1")] == "2"


@pytest.mark.asyncio
async def test_unrelated_event_type_is_ignored(fake_redis):
    event = {"event_type": "SomethingElse", "payload": {}}
    await handle_booking_event(fake_redis, event)
    assert fake_redis.store == {}
    assert fake_redis.published == []
