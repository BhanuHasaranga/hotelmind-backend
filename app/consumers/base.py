import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import ConsumerRecord
from redis.asyncio import Redis

from app.core.config import settings
from app.logging.structured import bind_context, reset_context
from app.metrics.prometheus import (
    consumer_errors_total,
    consumer_processing_seconds,
    consumer_retry_total,
    events_consumed_total,
)
from app.redis_cache.dashboard_cache import mark_event_seen

logger = logging.getLogger(__name__)

Handler = Callable[[dict], Awaitable[None]]


class BaseConsumer(ABC):
    """Wraps an AIOKafkaConsumer with retry/backoff, DLQ, idempotency,
    structured logging, and metrics. Subclasses declare `name` and `topics`
    and implement `handle(event_dict)`.
    """

    name: str
    topics: list[str]

    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._dlq_producer: AIOKafkaProducer | None = None
        self._redis: Redis | None = None
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def handle(self, event: dict) -> None:
        ...

    async def start(self) -> None:
        group_id = f"{settings.KAFKA_CONSUMER_GROUP_PREFIX}.{self.name}"
        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            client_id=f"{settings.KAFKA_CLIENT_ID}-{self.name}",
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        await self._consumer.start()

        self._dlq_producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=f"{settings.KAFKA_CLIENT_ID}-{self.name}-dlq",
        )
        await self._dlq_producer.start()

        self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

        logger.info("Consumer started", extra={"consumer": self.name, "topics": self.topics})

    async def stop(self) -> None:
        self._stop_event.set()
        if self._consumer is not None:
            await self._consumer.stop()
        if self._dlq_producer is not None:
            await self._dlq_producer.stop()
        if self._redis is not None:
            await self._redis.close()
        logger.info("Consumer stopped", extra={"consumer": self.name})

    async def run(self) -> None:
        await self.start()
        try:
            async for record in self._consumer:
                if self._stop_event.is_set():
                    break
                await self._process_record(record)
        finally:
            await self.stop()

    async def _process_record(self, record: ConsumerRecord) -> None:
        event = record.value
        event_id = event.get("event_id", str(uuid.uuid4()))
        trace_id = event.get("trace_id")
        correlation_id = event.get("correlation_id")

        tokens = bind_context(
            trace_id=trace_id,
            correlation_id=correlation_id,
            event_id=event_id,
            consumer=self.name,
            topic=record.topic,
        )
        start = time.monotonic()
        try:
            first_time = await mark_event_seen(self._redis, event_id)
            if not first_time:
                logger.info("Skipping duplicate event", extra={"event_id": event_id})
                return

            await self._process_with_retry(event)
            events_consumed_total.labels(topic=record.topic, consumer=self.name).inc()
        finally:
            elapsed = time.monotonic() - start
            consumer_processing_seconds.labels(topic=record.topic, consumer=self.name).observe(elapsed)
            reset_context(tokens)

    async def _process_with_retry(self, event: dict) -> None:
        attempt = 0
        while True:
            try:
                await self.handle(event)
                return
            except Exception:
                attempt += 1
                consumer_errors_total.labels(topic=self._current_topic(event), consumer=self.name).inc()
                if attempt > settings.KAFKA_MAX_RETRIES:
                    logger.exception(
                        "Exhausted retries, publishing to DLQ",
                        extra={"consumer": self.name, "attempt": attempt},
                    )
                    await self._publish_to_dlq(event)
                    return
                consumer_retry_total.labels(topic=self._current_topic(event), consumer=self.name).inc()
                backoff = min(
                    settings.KAFKA_RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
                    settings.KAFKA_RETRY_BACKOFF_MAX_SECONDS,
                )
                logger.warning(
                    "Handler raised, retrying",
                    extra={"consumer": self.name, "attempt": attempt, "backoff": backoff},
                )
                await asyncio.sleep(backoff)

    def _current_topic(self, event: dict) -> str:
        return self.topics[0] if self.topics else "unknown"

    async def _publish_to_dlq(self, event: dict) -> None:
        topic = self._current_topic(event)
        dlq_topic = f"{topic}{settings.KAFKA_DLQ_SUFFIX}"
        payload = json.dumps(event, default=str).encode("utf-8")
        await self._dlq_producer.send_and_wait(dlq_topic, value=payload)
