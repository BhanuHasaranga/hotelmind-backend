# Deployment

## Docker Compose (hotelmind-infra)

```bash
cd hotelmind-infra
cp .env.example .env
docker compose up -d --build
```

Services: `zookeeper`, `kafka` (KRaft-free, Zookeeper-based for simplicity),
`kafka-ui` (http://localhost:8080), `postgres`, `redis`, `backend`
(http://localhost:8000, runs `alembic upgrade head` then `uvicorn`),
`consumer-worker` (runs `python -m app.consumer_worker`, no exposed port).

Both `backend` and `consumer-worker` build from the same
`hotelmind-backend/Dockerfile` with different `command:` overrides.

### Bringing individual pieces up/down

```bash
docker compose up -d kafka redis postgres   # infra only, run backend locally
docker compose logs -f consumer-worker      # tail consumer logs
docker compose down -v                      # tear down + remove volumes
```

## Running without Docker

See the Quick start section in [README.md](./README.md). You still need a
Kafka broker and Redis reachable at `KAFKA_BOOTSTRAP_SERVERS` /
`REDIS_URL` — the simplest way to get those is
`docker compose up -d zookeeper kafka redis` from `hotelmind-infra` and run
everything else on the host.

## Database migrations

```bash
cd hotelmind-backend
alembic upgrade head
```

The Payment/Review tables are added by migration
`a1b2c3d4e5f6_add_payment_and_review_tables.py`, chained after the original
`ef06bda63819_initial_hotel_operational_schema.py`.

## Environment variables

See `hotelmind-infra/.env.example` for the full list; all map 1:1 to fields
on `app.core.config.Settings`.
