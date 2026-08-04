"""Fixtures for tests that exercise the real, already-running docker-compose
stack (postgres/kafka/redis/backend/consumer-worker) rather than testcontainers.

These are opt-in via the LIVE_STACK env var (set by default to "1" so they run
normally in CI/dev against `docker compose up`) and are skipped automatically
if the backend health endpoint is unreachable, so the rest of the suite still
passes on a machine with no stack running.
"""

import os

import httpx
import pytest
import pytest_asyncio

BASE_URL = os.environ.get("HOTELMIND_BASE_URL", "http://localhost:8000")
KAFKA_BOOTSTRAP = os.environ.get("HOTELMIND_KAFKA_BOOTSTRAP", "localhost:9092")
REDIS_URL = os.environ.get("HOTELMIND_REDIS_URL", "redis://localhost:6380/0")
WS_URL = os.environ.get("HOTELMIND_WS_URL", "ws://localhost:8000/ws/dashboard")


def _live_stack_reachable() -> bool:
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


requires_live_stack = pytest.mark.skipif(
    not _live_stack_reachable(),
    reason="Live docker-compose stack is not reachable at HOTELMIND_BASE_URL",
)


@pytest_asyncio.fixture
async def api_client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        yield client


@pytest_asyncio.fixture
async def seeded_branch(api_client: httpx.AsyncClient):
    """Returns (hotel, branch, room, guest) tuples from already-seeded data."""
    hotels = (await api_client.get("/api/v1/hotels/")).json()
    assert hotels, "expected seeded hotel data — run scripts/seed_data.py first"
    hotel = hotels[0]
    branch = hotel["branches"][0]
    rooms = (await api_client.get(f"/api/v1/hotels/branches/{branch['id']}/rooms")).json()
    assert rooms, "expected seeded rooms"
    guests = (await api_client.get("/api/v1/bookings/guests", params={"limit": 1})).json()
    assert guests, "expected seeded guests"
    return hotel, branch, rooms[0], guests[0]
