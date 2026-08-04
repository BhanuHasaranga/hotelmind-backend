"""Replay a Kafka topic from the beginning (or a given timestamp) through the
matching pure handler function(s) to rebuild the Redis read-model.

Usage:
    python -m app.stream_processing.replay --topic booking.events
    python -m app.stream_processing.replay --topic payment.events --from-timestamp 1735689600000
"""
import argparse
import asyncio
import json
import logging
import uuid

from aiokafka import AIOKafkaConsumer, TopicPartition
from redis.asyncio import Redis

from app.core.config import settings
from app.events.topics import (
    BOOKING_EVENTS,
    DASHBOARD_EVENTS,
    ML_PREDICTIONS,
    PAYMENT_EVENTS,
    RESTAURANT_EVENTS,
)
from app.handlers.booking_handlers import handle_booking_event
from app.handlers.dashboard_handlers import handle_dashboard_event
from app.handlers.ml_handlers import handle_ml_event
from app.handlers.occupancy_handlers import handle_occupancy_event
from app.handlers.restaurant_handlers import handle_restaurant_event
from app.handlers.revenue_handlers import handle_revenue_event
from app.logging.structured import configure_logging
from app.redis_cache.dashboard_cache import mark_event_seen

logger = logging.getLogger(__name__)

_TOPIC_HANDLERS = {
    BOOKING_EVENTS: [handle_booking_event, handle_revenue_event, handle_occupancy_event],
    PAYMENT_EVENTS: [handle_revenue_event],
    RESTAURANT_EVENTS: [handle_restaurant_event],
    ML_PREDICTIONS: [handle_ml_event],
    DASHBOARD_EVENTS: [handle_dashboard_event],
}


async def replay(topic: str, from_timestamp: int | None) -> None:
    configure_logging()
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    handlers = _TOPIC_HANDLERS.get(topic, [])
    if not handlers:
        logger.warning("No handlers registered for topic; nothing to replay", extra={"topic": topic})
        return

    group_id = f"{settings.KAFKA_CONSUMER_GROUP_PREFIX}.replay.{uuid.uuid4().hex[:8]}"
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        client_id=f"{settings.KAFKA_CLIENT_ID}-replay",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    processed = 0
    skipped_malformed = 0
    skipped_duplicate = 0
    try:
        if from_timestamp is not None:
            partitions = consumer.partitions_for_topic(topic) or set()
            tps = [TopicPartition(topic, p) for p in partitions]
            offsets = await consumer.offsets_for_times({tp: from_timestamp for tp in tps})
            for tp, offset_and_ts in offsets.items():
                if offset_and_ts is not None:
                    consumer.seek(tp, offset_and_ts.offset)

        async for record in consumer:
            try:
                event = json.loads(record.value.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                skipped_malformed += 1
                logger.warning("Skipping malformed message during replay", extra={"topic": topic})
                continue

            event_id = event.get("event_id", str(uuid.uuid4()))
            first_time = await mark_event_seen(redis, f"replay.{topic}", event_id)
            if not first_time:
                skipped_duplicate += 1
                continue

            for handler in handlers:
                await handler(redis, event)
            processed += 1
            if processed % 100 == 0:
                logger.info("Replay progress", extra={"processed": processed})
    finally:
        await consumer.stop()
        await redis.close()
        logger.info(
            "Replay complete",
            extra={
                "topic": topic,
                "processed": processed,
                "skipped_malformed": skipped_malformed,
                "skipped_duplicate": skipped_duplicate,
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a Kafka topic to rebuild the Redis read-model")
    parser.add_argument("--topic", required=True, help="Kafka topic to replay")
    parser.add_argument("--from-timestamp", type=int, default=None, help="Unix epoch ms to seek from")
    args = parser.parse_args()
    asyncio.run(replay(args.topic, args.from_timestamp))


if __name__ == "__main__":
    main()
