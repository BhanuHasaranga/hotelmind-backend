import pytest

from app.handlers.revenue_handlers import handle_revenue_event
from app.redis_cache.keys import revenue_key


@pytest.mark.asyncio
async def test_reservation_created_adds_revenue(fake_redis):
    event = {
        "event_type": "ReservationCreated",
        "payload": {"branch_id": "b1", "total_amount": "100.00"},
    }
    await handle_revenue_event(fake_redis, event)
    assert fake_redis.store[revenue_key("b1")] == "100.00"


@pytest.mark.asyncio
async def test_refund_issued_subtracts_revenue(fake_redis):
    fake_redis.store[revenue_key("b1")] = "100.00"
    event = {"event_type": "RefundIssued", "payload": {"branch_id": "b1", "amount": "30.00"}}
    await handle_revenue_event(fake_redis, event)
    assert fake_redis.store[revenue_key("b1")] == "70.00"


@pytest.mark.asyncio
async def test_revenue_never_goes_negative(fake_redis):
    fake_redis.store[revenue_key("b1")] = "10.00"
    event = {"event_type": "RefundIssued", "payload": {"branch_id": "b1", "amount": "50.00"}}
    await handle_revenue_event(fake_redis, event)
    assert fake_redis.store[revenue_key("b1")] == "0"
