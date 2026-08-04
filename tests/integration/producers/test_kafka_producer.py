import uuid

import pytest

from tests.integration.conftest import requires_docker

pytest.importorskip("testcontainers")


@requires_docker
@pytest.mark.asyncio
async def test_kafka_producer_publishes_and_is_consumable():
    from aiokafka import AIOKafkaConsumer
    from testcontainers.kafka import KafkaContainer

    from app.events.schemas import BaseEvent
    from app.events.topics import BOOKING_EVENTS
    from app.producers.kafka_producer import KafkaEventPublisher

    with KafkaContainer() as kafka:
        bootstrap = kafka.get_bootstrap_server()

        import app.core.config as config_module
        config_module.settings.KAFKA_BOOTSTRAP_SERVERS = bootstrap

        publisher = KafkaEventPublisher()
        await publisher.start()
        try:
            event = BaseEvent(
                event_type="ReservationCreated",
                aggregate_type="Reservation",
                aggregate_id=str(uuid.uuid4()),
                payload={"foo": "bar"},
            )
            await publisher.publish(event, BOOKING_EVENTS)
        finally:
            await publisher.stop()

        consumer = AIOKafkaConsumer(
            BOOKING_EVENTS,
            bootstrap_servers=bootstrap,
            auto_offset_reset="earliest",
            group_id="test-group",
        )
        await consumer.start()
        try:
            msg = await consumer.getone()
            assert b"ReservationCreated" in msg.value
        finally:
            await consumer.stop()
