import json
import logging

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.events.schemas import BaseEvent
from app.metrics.prometheus import events_produced_total
from app.producers.base import EventPublisher

logger = logging.getLogger(__name__)


def _serialize(event: BaseEvent) -> bytes:
    return event.model_dump_json().encode("utf-8")


class KafkaEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_CLIENT_ID,
            value_serializer=_serialize,
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        try:
            await producer.start()
        except Exception:
            logger.warning(
                "Kafka unavailable, continuing without event publishing",
                extra={"bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS},
                exc_info=True,
            )
            return
        self._producer = producer
        logger.info("Kafka producer started", extra={"bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS})

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(self, event: BaseEvent, topic: str) -> None:
        if self._producer is None:
            logger.debug("Kafka producer unavailable, dropping event", extra={"topic": topic})
            return
        await self._producer.send_and_wait(topic, value=event, key=event.aggregate_id)
        events_produced_total.labels(topic=topic, event_type=event.event_type).inc()
