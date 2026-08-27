import asyncio
import json
import logging

from redis.asyncio import Redis

from app.core.config import settings
from app.redis_cache.keys import DASHBOARD_UPDATES_CHANNEL
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


async def redis_pubsub_listener(manager: ConnectionManager) -> None:
    """Subscribes to the dashboard:updates Redis Pub/Sub channel and fans out
    incoming messages to connected WebSocket clients. Runs as a background task
    in the API process's lifespan - this is how DashboardConsumer (a separate
    process) reaches WebSocket clients without cross-process coupling.
    """
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(DASHBOARD_UPDATES_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                logger.warning("Dropping malformed dashboard update message")
                continue
            await manager.broadcast(payload)
    except asyncio.CancelledError:
        raise
    finally:
        await pubsub.unsubscribe(DASHBOARD_UPDATES_CHANNEL)
        await pubsub.close()
        await redis.close()
