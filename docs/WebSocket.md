# WebSocket

## Endpoint

`GET /ws/dashboard` — clients connect and receive JSON-encoded dashboard
update messages pushed from the server. There is no client → server protocol;
the server only reads (and discards) incoming frames to detect disconnects.

## Message shape

Every broadcast message is whatever was published onto the `dashboard:updates`
Redis Pub/Sub channel by a consumer handler, e.g.:

```json
{ "type": "booking", "event_type": "ReservationCreated", "payload": { "...": "..." } }
{ "type": "occupancy_changed", "branch_id": "...", "occupancy_pct": 72.5 }
{ "type": "forecast", "forecast_type": "OccupancyForecast", "branch_id": "...", "data": { "...": "..." } }
```

## How it works

1. `app/websocket/manager.py` — `ConnectionManager` tracks connected
   `WebSocket` objects and exposes `broadcast(payload)`.
2. `app/websocket/router.py` — the `/ws/dashboard` route accepts connections
   and registers them with a module-level `ConnectionManager` instance.
3. `app/websocket/pubsub_bridge.py` — `redis_pubsub_listener()` runs as a
   background task started in `app/main.py`'s lifespan. It subscribes to the
   `dashboard:updates` Redis channel and calls `manager.broadcast()` for every
   message received.
4. Consumers (running in the separate `consumer_worker` process) never talk to
   WebSocket clients directly — they only publish to Redis. This is what
   lets the API and consumer-worker processes/containers scale independently.

## Metrics

`websocket_connections` (gauge) and `websocket_messages_sent_total` (counter)
are updated by `ConnectionManager`.

## Frontend

`hotelmind-frontend/lib/useDashboardSocket.ts` is a small React hook that
opens the WebSocket, auto-reconnects on close (3s backoff), and exposes
`{ lastUpdate, connected }`. It's wired into
`app/(app)/dashboard/page.tsx` via `components/dashboard/LiveOccupancyBadge.tsx`,
which shows a live-updating occupancy percentage without polling.
