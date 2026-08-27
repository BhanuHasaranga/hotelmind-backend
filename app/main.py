import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 - ensures all SQLAlchemy models register before mapper config
from app.core.config import settings
from app.logging.structured import configure_logging
from app.producers.kafka_producer import KafkaEventPublisher
from app.routers import auth as auth_router
from app.routers import health as health_router
from app.routers import hotels as hotels_router
from app.routers import bookings as bookings_router
from app.routers import restaurant as restaurant_router
from app.routers import staff as staff_router
from app.routers import dashboard as dashboard_router
from app.routers import payments as payments_router
from app.routers import reviews as reviews_router
from app.routers import ml as ml_router
from app.routers import recommendations as recommendations_router
from app.metrics import router as metrics_router
from app.websocket import router as websocket_router
from app.websocket.pubsub_bridge import redis_pubsub_listener

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    publisher = KafkaEventPublisher()
    await publisher.start()
    app.state.event_publisher = publisher

    bridge_task = asyncio.create_task(redis_pubsub_listener(websocket_router.manager))

    yield

    bridge_task.cancel()
    try:
        await bridge_task
    except asyncio.CancelledError:
        pass
    await publisher.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router.router)
    app.include_router(auth_router.router, prefix="/api/v1")
    app.include_router(hotels_router.router, prefix="/api/v1")
    app.include_router(hotels_router.branches_router, prefix="/api/v1")
    app.include_router(bookings_router.router, prefix="/api/v1")
    app.include_router(restaurant_router.router, prefix="/api/v1")
    app.include_router(staff_router.router, prefix="/api/v1")
    app.include_router(dashboard_router.router, prefix="/api/v1")
    app.include_router(payments_router.router, prefix="/api/v1")
    app.include_router(reviews_router.router, prefix="/api/v1")
    app.include_router(ml_router.router, prefix="/api/v1")
    app.include_router(recommendations_router.router, prefix="/api/v1")
    app.include_router(metrics_router.router)
    app.include_router(websocket_router.router)

    return app


app = create_app()
