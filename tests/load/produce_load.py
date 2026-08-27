"""Simple asyncio load generator for manual testing - not a pytest test.

Usage:
    python -m tests.load.produce_load --count 1000 --rate 100
"""
import argparse
import asyncio
import time
import uuid

from app.events.schemas import BaseEvent, ReservationCreated
from app.events.topics import BOOKING_EVENTS
from app.producers.kafka_producer import KafkaEventPublisher


async def produce(count: int, rate: float) -> None:
    publisher = KafkaEventPublisher()
    await publisher.start()
    interval = 1.0 / rate if rate > 0 else 0
    start = time.monotonic()
    try:
        for i in range(count):
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
                    total_amount="199.99",
                ).model_dump(mode="json"),
            )
            await publisher.publish(event, BOOKING_EVENTS)
            if (i + 1) % 100 == 0:
                print(f"Published {i + 1}/{count}")
            if interval:
                await asyncio.sleep(interval)
    finally:
        await publisher.stop()
    elapsed = time.monotonic() - start
    print(f"Done: {count} events in {elapsed:.2f}s ({count / elapsed:.1f} events/sec)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fire N events at a target rate for load testing")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--rate", type=float, default=100.0, help="events per second, 0 = unthrottled")
    args = parser.parse_args()
    asyncio.run(produce(args.count, args.rate))


if __name__ == "__main__":
    main()
