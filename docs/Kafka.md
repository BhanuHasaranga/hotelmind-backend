# Kafka

## Topics

| Topic | Producers | Consumers |
|---|---|---|
| `booking.events` | BookingService | BookingConsumer, RevenueConsumer, OccupancyConsumer, NotificationConsumer, AuditConsumer |
| `payment.events` | PaymentService | RevenueConsumer, NotificationConsumer, AuditConsumer |
| `restaurant.events` | RestaurantService | RestaurantConsumer, AuditConsumer |
| `staff.events` | (reserved for future staff-domain events) | AuditConsumer |
| `review.events` | ReviewService | NotificationConsumer, AuditConsumer |
| `ml.predictions` | (external ML pipeline, not in this repo) | MLConsumer, AuditConsumer |
| `dashboard.events` | (aggregation/ML jobs) | DashboardConsumer, AuditConsumer |
| `notification.events` | (reserved) | AuditConsumer |
| `audit.events` | (reserved) | — |

Every topic also has a corresponding `<topic>.dlq` topic that consumers
publish to after exhausting retries (`KAFKA_DLQ_SUFFIX` in settings).

## Event envelope

Every message on every topic is a JSON-serialized `BaseEvent`
(`app/events/schemas.py`):

```json
{
  "event_id": "uuid",
  "event_type": "ReservationCreated",
  "aggregate_type": "Reservation",
  "aggregate_id": "uuid-as-string",
  "version": 1,
  "timestamp": "2026-08-04T00:00:00Z",
  "source": "hotelmind-backend",
  "payload": { "...": "event-type-specific fields" },
  "metadata": {},
  "trace_id": "uuid",
  "correlation_id": "uuid | null"
}
```

Kafka message key = `aggregate_id`, so all events for the same aggregate land
on the same partition and are processed in order per-aggregate.

## Producer

`app/producers/kafka_producer.py` — `KafkaEventPublisher` wraps
`AIOKafkaProducer`, started/stopped in the API process's lifespan. Every
`publish()` call increments `events_produced_total{topic,event_type}`.

## Consumer base (`app/consumers/base.py`)

Each concrete consumer subclasses `BaseConsumer` and provides `name` and
`topics`. The base class handles:

- **Idempotency**: `SETNX event:seen:{event_id}` in Redis before processing;
  duplicates are skipped and logged.
- **Retry with exponential backoff**: on handler exception, retries up to
  `KAFKA_MAX_RETRIES` times with backoff
  `min(KAFKA_RETRY_BACKOFF_BASE_SECONDS * 2^attempt, KAFKA_RETRY_BACKOFF_MAX_SECONDS)`.
- **DLQ**: after exhausting retries, publishes the raw event to
  `{topic}{KAFKA_DLQ_SUFFIX}`.
- **Structured logging**: binds `trace_id`/`correlation_id`/`event_id`/
  `consumer`/`topic` into every log line for the duration of processing.
- **Metrics**: `events_consumed_total`, `consumer_errors_total`,
  `consumer_retry_total`, `consumer_processing_seconds`.
- **Graceful shutdown**: `stop()` sets an `asyncio.Event` and closes the
  underlying `AIOKafkaConsumer`/`AIOKafkaProducer`/Redis connections.

Handler logic itself lives in `app/handlers/*.py` as plain async functions
`(redis, event_dict) -> None` — no Kafka objects involved — so it's directly
unit-testable and reusable from `stream_processing/replay.py`.

## Running the consumer fleet

```bash
python -m app.consumer_worker
```

Starts all 8 consumers as asyncio tasks and handles SIGTERM/SIGINT for
graceful shutdown.
