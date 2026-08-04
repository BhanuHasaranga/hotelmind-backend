# Architecture

## Overview

```
Next.js Dashboard --(WS)--> FastAPI /ws/dashboard
FastAPI routers -> Services -> Repositories -> Postgres (unchanged)
Services -> EventPublisher (after repo commit) -> Kafka topics
Kafka topics -> Consumers (aiokafka, separate process) -> Redis (read-model) + Redis Pub/Sub
Redis Pub/Sub (dashboard:updates) -> FastAPI process -> WebSocket broadcast
Consumers -> DLQ topics on exhausted retries
```

## Process model

Two separate processes run from the same codebase and Docker image:

1. **API process** (`uvicorn app.main:app`) — serves HTTP + WebSocket traffic.
   Owns the `KafkaEventPublisher` (producer only) and a background task that
   subscribes to the `dashboard:updates` Redis Pub/Sub channel, fanning
   messages out to connected WebSocket clients via `ConnectionManager`.
2. **Consumer worker process** (`python -m app.consumer_worker`) — runs all 8
   consumers as asyncio tasks. Never touches the API's WebSocket connections
   directly.

This split is production-correct: consumers can be scaled independently of
the API, a slow/misbehaving consumer can't block request handling, and
graceful shutdown (SIGTERM/SIGINT) is isolated per process.

**Why Redis Pub/Sub for the WebSocket bridge?** The `DashboardConsumer` runs
in a different process (and, in production, likely a different container/pod)
than the WebSocket server. Rather than couple consumers directly to
WebSocket connections, `DashboardConsumer` publishes normalized updates to
the `dashboard:updates` Redis channel; the API process is the only thing
that needs to know about WebSocket clients.

## Layering (unchanged, extended)

Router → Service → Repository → Model, per existing convention. Services now
also take an `EventPublisher` constructor argument and call `publish()`
**after** the repository call that performs the commit — never before, so we
never publish an event for a change that didn't actually persist.

## New domains

`Payment` and `Review` were added as minimal domains (model + repository +
service + router) purely to give `PaymentCompleted`/`RefundIssued` and
`ReviewCreated`/`SentimentCalculated` events something real to originate
from. Sentiment scoring is a trivial keyword lexicon, not a real ML model —
intentionally out of scope for this phase.

## Topics

See [Kafka.md](./Kafka.md) for the full topic list and per-topic producers/consumers.
