import json
import uuid

import pytest

from tests.integration.conftest import requires_docker

pytest.importorskip("testcontainers")


@requires_docker
@pytest.mark.asyncio
async def test_booking_consumer_updates_redis_from_kafka_event():
    from aiokafka import AIOKafkaProducer
    from testcontainers.kafka import KafkaContainer
    from testcontainers.redis import RedisContainer

    from app.consumers.booking_consumer import BookingConsumer
    import app.core.config as config_module

    with KafkaContainer() as kafka, RedisContainer() as redis_container:
        bootstrap = kafka.get_bootstrap_server()
        config_module.settings.KAFKA_BOOTSTRAP_SERVERS = bootstrap
        config_module.settings.REDIS_URL = (
            f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"
        )

        producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
        await producer.start()
        branch_id = str(uuid.uuid4())
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "ReservationCreated",
            "aggregate_type": "Reservation",
            "aggregate_id": str(uuid.uuid4()),
            "payload": {"branch_id": branch_id},
        }
        await producer.send_and_wait("booking.events", json.dumps(event).encode("utf-8"))
        await producer.stop()

        consumer = BookingConsumer()
        await consumer.start()
        try:
            record = await consumer._consumer.getone()
            await consumer._process_record(record)
        finally:
            await consumer.stop()

        from redis.asyncio import Redis

        redis = Redis.from_url(config_module.settings.REDIS_URL, decode_responses=True)
        value = await redis.get(f"dashboard:booking_count:{branch_id}")
        assert value == "1"
        await redis.close()
