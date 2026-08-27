# Troubleshooting

**Consumer never processes anything / group stuck at 0 lag with no messages**
Check `KAFKA_AUTO_OFFSET_RESET` - with `earliest`, a brand new consumer
group will replay the entire topic; with `latest`, it only sees new
messages. Verify with Kafka UI (http://localhost:8080) that the topic
actually has messages and the consumer group is subscribed.

**Events published but Redis keys never update**
Confirm the `consumer-worker` process/container is actually running -
consumers are *not* started by the API process. `docker compose ps` should
show `consumer-worker` as `Up`.

**WebSocket connects but never receives messages**
The API process's `dashboard:updates` Redis Pub/Sub bridge is started in
`app/main.py`'s lifespan (`redis_pubsub_listener`). If it crashed silently,
restart the API process. Also confirm `DashboardConsumer` is running and
actually receiving `dashboard.events` - it's the only consumer that
publishes to `dashboard:updates` directly (other consumers update read-model
keys but don't all publish to the same channel - check `app/handlers/*.py`
for which ones call `publish_dashboard_update`).

**Messages piling up in a `.dlq` topic**
That means a handler is raising after `KAFKA_MAX_RETRIES` retries. Inspect
the DLQ topic in Kafka UI, find the offending payload, and check consumer
logs (structured JSON, filter by `consumer` field) for the exception. Once
fixed, replay the DLQ manually or fix forward and use
`stream_processing/replay.py` to rebuild any affected Redis keys.

**Duplicate processing despite idempotency check**
`event:seen:{event_id}` has a 24h TTL - if the same `event_id` is replayed
more than 24h later (e.g. via `replay.py` against very old Kafka retention),
it will be treated as new. This is intentional for replay to work at all;
if you need permanent dedup, increase the TTL in
`app/redis_cache/dashboard_cache.mark_event_seen`.

**`pip install` fails to build `aiokafka`/`pydantic-core` from source**
On Windows, make sure you're using a Python version with prebuilt wheels
available for the pinned versions (3.11–3.13 as of this writing). Building
from source requires a working Rust toolchain and MSVC linker; prefer a
matching prebuilt wheel instead of fighting the compiler.

**Integration tests all skip**
They're gated on Docker being available (`tests/integration/conftest.py`
runs `docker info`). Start Docker Desktop / the Docker daemon and re-run
`pytest`.
