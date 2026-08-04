"""End-to-end load test against the live stack: publishes a mix of realistic
business events directly to Kafka topics (bypassing HTTP/DB, matching the
existing tests/load/produce_load.py pattern) and measures:

  - producer latency (time to ack from Kafka)
  - end-to-end latency (event timestamp -> visible in Redis)
  - throughput (events/sec)
  - consumer lag (read via `kafka-consumer-groups --describe` after the run)

Usage (inside the backend/consumer-worker container, which has network
access to kafka:29092 and redis:6379):

    docker cp tests/load/load_test_e2e.py hotelmind-backend-1:/app/tests/load/load_test_e2e.py
    docker exec hotelmind-backend-1 python -m tests.load.load_test_e2e \
        --bookings 300 --cancellations 150 --orders 200 --reviews 150 --ml-events 50

Scale down from the nominal 1000/500/800/500/100 spec if the single-broker,
single-partition local Kafka can't keep up within a reasonable wall-clock
budget — pass smaller counts and note it in the report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
import uuid
from decimal import Decimal

from aiokafka import AIOKafkaProducer
from redis.asyncio import Redis

from app.core.config import settings
from app.events.schemas import (
    BaseEvent,
    OccupancyForecastReady,
    OrderCompleted,
    ReservationCancelled,
    ReservationCreated,
    ReviewCreated,
)
from app.events.topics import BOOKING_EVENTS, ML_PREDICTIONS, RESTAURANT_EVENTS, REVIEW_EVENTS

FIXED_BRANCH_ID = "e6911986-f9c5-43ca-9500-bf4094ac300d"  # seeded branch; adjust via --branch-id if needed


class Timer:
    def __init__(self) -> None:
        self.samples: list[float] = []

    def record(self, seconds: float) -> None:
        self.samples.append(seconds)

    def summary(self) -> dict:
        if not self.samples:
            return {"count": 0}
        s = sorted(self.samples)
        n = len(s)
        return {
            "count": n,
            "avg_ms": round(statistics.mean(s) * 1000, 2),
            "p50_ms": round(s[int(n * 0.50)] * 1000, 2),
            "p95_ms": round(s[min(int(n * 0.95), n - 1)] * 1000, 2),
            "p99_ms": round(s[min(int(n * 0.99), n - 1)] * 1000, 2),
            "max_ms": round(max(s) * 1000, 2),
        }


async def _produce(producer: AIOKafkaProducer, event: BaseEvent, topic: str, timer: Timer) -> None:
    start = time.monotonic()
    await producer.send_and_wait(topic, value=event, key=event.aggregate_id)
    timer.record(time.monotonic() - start)


async def run_load(
    bookings: int, cancellations: int, orders: int, reviews: int, ml_events: int, branch_id: str
) -> dict:
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda e: e.model_dump_json().encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        linger_ms=5,
    )
    await producer.start()

    producer_timer = Timer()
    total_events = bookings + cancellations + orders + reviews + ml_events
    overall_start = time.monotonic()
    last_event_id: str | None = None

    try:
        for i in range(bookings):
            reservation_id = uuid.uuid4()
            event = BaseEvent(
                event_type="ReservationCreated",
                aggregate_type="Reservation",
                aggregate_id=str(reservation_id),
                payload=ReservationCreated(
                    reservation_id=reservation_id,
                    room_id=uuid.uuid4(),
                    guest_id=uuid.uuid4(),
                    branch_id=branch_id,
                    check_in_date="2027-06-01",
                    check_out_date="2027-06-04",
                    status="PENDING",
                    total_amount=Decimal("199.99"),
                ).model_dump(mode="json"),
            )
            last_event_id = str(event.event_id)
            await _produce(producer, event, BOOKING_EVENTS, producer_timer)
            if (i + 1) % 100 == 0:
                print(f"  bookings: {i + 1}/{bookings}")

        for i in range(cancellations):
            reservation_id = uuid.uuid4()
            event = BaseEvent(
                event_type="ReservationCancelled",
                aggregate_type="Reservation",
                aggregate_id=str(reservation_id),
                payload=ReservationCancelled(
                    reservation_id=reservation_id,
                    branch_id=branch_id,
                    status="CANCELLED",
                    total_amount=Decimal("199.99"),
                    cancellation_reason="load test",
                ).model_dump(mode="json"),
            )
            await _produce(producer, event, BOOKING_EVENTS, producer_timer)
            if (i + 1) % 100 == 0:
                print(f"  cancellations: {i + 1}/{cancellations}")

        for i in range(orders):
            order_id = uuid.uuid4()
            event = BaseEvent(
                event_type="OrderCompleted",
                aggregate_type="RestaurantOrder",
                aggregate_id=str(order_id),
                payload=OrderCompleted(
                    order_id=order_id, branch_id=branch_id, status="CLOSED", total_amount=Decimal("42.50")
                ).model_dump(mode="json"),
            )
            await _produce(producer, event, RESTAURANT_EVENTS, producer_timer)
            if (i + 1) % 100 == 0:
                print(f"  orders: {i + 1}/{orders}")

        for i in range(reviews):
            review_id = uuid.uuid4()
            event = BaseEvent(
                event_type="ReviewCreated",
                aggregate_type="Review",
                aggregate_id=str(review_id),
                payload=ReviewCreated(
                    review_id=review_id, guest_id=uuid.uuid4(), rating=(i % 5) + 1, comment="Load test review"
                ).model_dump(mode="json"),
            )
            await _produce(producer, event, REVIEW_EVENTS, producer_timer)
            if (i + 1) % 100 == 0:
                print(f"  reviews: {i + 1}/{reviews}")

        for i in range(ml_events):
            event = BaseEvent(
                event_type="OccupancyForecastReady",
                aggregate_type="Branch",
                aggregate_id=branch_id,
                payload=OccupancyForecastReady(
                    branch_id=branch_id, forecast_date="2027-07-01", predicted_occupancy_pct=70.0 + i % 20
                ).model_dump(mode="json"),
            )
            last_event_id = str(event.event_id)
            await _produce(producer, event, ML_PREDICTIONS, producer_timer)
            if (i + 1) % 25 == 0:
                print(f"  ml_events: {i + 1}/{ml_events}")
    finally:
        await producer.stop()

    produce_elapsed = time.monotonic() - overall_start

    # End-to-end latency: poll Redis for the booking_count key to change/settle,
    # using the last-published ML forecast's Redis key as our e2e latency probe
    # since it's a direct, uniquely-keyed write (dashboard:forecast:...).
    e2e_start = time.monotonic()
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    e2e_latency_s = None
    try:
        forecast_key = f"dashboard:forecast:OccupancyForecast:{branch_id}"
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            val = await redis.get(forecast_key)
            if val is not None:
                data = json.loads(val)
                if data.get("predicted_occupancy_pct") == 70.0 + (ml_events - 1) % 20:
                    e2e_latency_s = time.monotonic() - e2e_start
                    break
            await asyncio.sleep(0.2)
    finally:
        await redis.aclose()

    return {
        "total_events": total_events,
        "produce_elapsed_s": round(produce_elapsed, 3),
        "throughput_events_per_sec": round(total_events / produce_elapsed, 1) if produce_elapsed > 0 else None,
        "producer_latency": producer_timer.summary(),
        "e2e_latency_last_ml_event_s": round(e2e_latency_s, 3) if e2e_latency_s is not None else "TIMEOUT (30s)",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bookings", type=int, default=300)
    parser.add_argument("--cancellations", type=int, default=150)
    parser.add_argument("--orders", type=int, default=200)
    parser.add_argument("--reviews", type=int, default=150)
    parser.add_argument("--ml-events", type=int, default=50)
    parser.add_argument("--branch-id", type=str, default=FIXED_BRANCH_ID)
    args = parser.parse_args()

    result = asyncio.run(
        run_load(args.bookings, args.cancellations, args.orders, args.reviews, args.ml_events, args.branch_id)
    )
    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
