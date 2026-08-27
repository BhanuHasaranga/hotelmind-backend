# HotelMind Backend - Phase 7: Event-Driven Architecture

This adds a Kafka-based event-driven layer on top of the existing FastAPI +
Postgres backend: domain writes publish events, a fleet of consumers project
those events into a Redis read-model, and a WebSocket endpoint pushes live
updates to the dashboard.

## Contents

- [Architecture.md](./Architecture.md) - system overview, process model
- [Kafka.md](./Kafka.md) - topics, producers, consumers, DLQ/retry
- [WebSocket.md](./WebSocket.md) - `/ws/dashboard` and the Redis pub/sub bridge
- [Redis.md](./Redis.md) - key naming, cache-aside pattern, idempotency
- [SequenceDiagrams.md](./SequenceDiagrams.md) - Mermaid diagrams for every flow
- [Deployment.md](./Deployment.md) - Docker/compose, running locally
- [Troubleshooting.md](./Troubleshooting.md) - common issues

## Quick start

```bash
cd hotelmind-infra
cp .env.example .env
docker compose up -d
```

Then visit:
- API docs: http://localhost:8000/docs
- Kafka UI: http://localhost:8080
- Metrics: http://localhost:8000/metrics

## Local development (without Docker)

```bash
cd hotelmind-backend
python -m venv .venv
.venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
# in a second terminal, run the consumer fleet:
python -m app.consumer_worker
```

Requires a running Kafka broker and Redis instance (see `hotelmind-infra/docker-compose.yml`).

## Tests

```bash
pytest
```

Unit tests (`tests/unit/`) run with no external dependencies. Integration
tests (`tests/integration/`) use `testcontainers` and are skipped
automatically if Docker isn't available.
