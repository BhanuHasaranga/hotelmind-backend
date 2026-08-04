import asyncio
import logging
import signal

from prometheus_client import start_http_server

from app.metrics.prometheus import registry
from app.consumers.audit_consumer import AuditConsumer
from app.consumers.base import BaseConsumer
from app.consumers.booking_consumer import BookingConsumer
from app.consumers.dashboard_consumer import DashboardConsumer
from app.consumers.ml_consumer import MLConsumer
from app.consumers.notification_consumer import NotificationConsumer
from app.consumers.occupancy_consumer import OccupancyConsumer
from app.consumers.restaurant_consumer import RestaurantConsumer
from app.consumers.revenue_consumer import RevenueConsumer
from app.logging.structured import configure_logging

logger = logging.getLogger(__name__)

CONSUMER_CLASSES: list[type[BaseConsumer]] = [
    BookingConsumer,
    RevenueConsumer,
    OccupancyConsumer,
    RestaurantConsumer,
    MLConsumer,
    DashboardConsumer,
    NotificationConsumer,
    AuditConsumer,
]


METRICS_PORT = 9100


async def main() -> None:
    configure_logging()
    start_http_server(METRICS_PORT, registry=registry)
    logger.info("Consumer metrics server started", extra={"port": METRICS_PORT})
    consumers = [cls() for cls in CONSUMER_CLASSES]
    tasks = [asyncio.create_task(c.run(), name=c.name) for c in consumers]

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # add_signal_handler is unavailable on Windows event loops
            signal.signal(sig, lambda *_: stop_event.set())

    await stop_event.wait()

    logger.info("Stopping all consumers")
    for consumer in consumers:
        await consumer.stop()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Consumer worker shut down cleanly")


if __name__ == "__main__":
    asyncio.run(main())
