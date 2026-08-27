# Redis

Redis serves two purposes in Phase 7:

1. **Read-model / cache** for the dashboard (`app/redis_cache/`).
2. **Pub/Sub bridge** between the consumer-worker process and the API's
   WebSocket server (`dashboard:updates` channel).
3. **Idempotency store** for consumers (`event:seen:{event_id}`).

## Key naming (`app/redis_cache/keys.py`)

| Key | Purpose |
|---|---|
| `dashboard:summary:{branch_id}` | Cached `DashboardSummary` JSON |
| `dashboard:occupancy:{branch_id}` | Current occupancy % |
| `dashboard:revenue:{branch_id}` | Running revenue total |
| `dashboard:booking_count:{branch_id}` | Running booking count |
| `dashboard:restaurant_sales:{branch_id}` | Running restaurant sales total |
| `dashboard:forecast:{forecast_type}:{branch_id}` | Latest ML forecast payload |
| `dashboard:ai_insight:{insight_id}` | Latest AI insight payload |
| `event:seen:{event_id}` | Idempotency marker (24h TTL) |
| `dashboard:updates` (channel, not a key) | Pub/Sub channel for WebSocket fan-out |

## Cache-aside pattern

`app/services/dashboard.py`'s `get_summary()`:

1. Try `dashboard_cache.get_summary(redis, branch_id)`.
2. On hit, return immediately (`redis_cache_hits` metric incremented).
3. On miss (`redis_cache_misses` incremented), fall back to the original
   Postgres aggregation queries, then **backfill** the cache with a 5-minute
   TTL so subsequent requests hit Redis.

The individual metric keys (`occupancy`, `revenue`, `booking_count`,
`restaurant_sales`) are written incrementally by consumer handlers as events
arrive - they represent a live running read-model, separate from the
periodically-refreshed `summary` cache entry.

## Idempotency

`app/consumers/base.py` calls `mark_event_seen()` (a `SET NX EX` - atomic
"set if not exists") before invoking a handler. If the event was already
seen (e.g. re-delivered after a consumer restart before offset commit), the
handler is skipped entirely and the message is treated as done.

## Rebuilding the read-model

If Redis is flushed or a new consumer group needs to catch up from scratch,
`app/stream_processing/replay.py` re-reads a topic from the beginning and
re-runs each event through the same pure handler functions, deterministically
rebuilding the affected keys. See [SequenceDiagrams.md](./SequenceDiagrams.md#replay-flow).
