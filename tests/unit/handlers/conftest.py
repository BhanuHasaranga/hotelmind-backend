import pytest


class FakeRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis, covering only the
    operations used by handlers/dashboard_cache so pure handler logic can be
    unit tested without a real Redis instance.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.published: list[tuple[str, str]] = []
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def publish(self, channel: str, message: str):
        self.published.append((channel, message))

    async def lpush(self, key: str, value: str):
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int):
        if key in self.lists:
            self.lists[key] = self.lists[key][start : end + 1]


@pytest.fixture
def fake_redis():
    return FakeRedis()
