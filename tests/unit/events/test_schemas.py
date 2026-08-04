import uuid

from app.events.schemas import BaseEvent, ReservationCreated
from app.events.topics import ALL_TOPICS, BOOKING_EVENTS


def test_base_event_defaults():
    event = BaseEvent(
        event_type="ReservationCreated",
        aggregate_type="Reservation",
        aggregate_id=str(uuid.uuid4()),
    )
    assert event.version == 1
    assert event.source == "hotelmind-backend"
    assert event.payload == {}
    assert event.metadata == {}
    assert event.trace_id is not None
    assert event.correlation_id is None


def test_base_event_serializes_to_json():
    event = BaseEvent(
        event_type="ReservationCreated",
        aggregate_type="Reservation",
        aggregate_id="abc",
        payload={"foo": "bar"},
    )
    raw = event.model_dump_json()
    assert "ReservationCreated" in raw
    assert "abc" in raw


def test_reservation_created_payload_roundtrip():
    payload = ReservationCreated(
        reservation_id=uuid.uuid4(),
        room_id=uuid.uuid4(),
        guest_id=uuid.uuid4(),
        check_in_date="2026-01-01",
        check_out_date="2026-01-05",
        status="PENDING",
        total_amount="450.00",
    )
    dumped = payload.model_dump(mode="json")
    assert dumped["status"] == "PENDING"
    assert dumped["total_amount"] == "450.00"


def test_booking_events_topic_in_all_topics():
    assert BOOKING_EVENTS in ALL_TOPICS
    assert len(ALL_TOPICS) == 9
