from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — ensures all SQLAlchemy models register before mapper config
from app.core.config import settings
from app.routers import health as health_router
from app.routers import hotels as hotels_router
from app.routers import bookings as bookings_router
from app.routers import restaurant as restaurant_router
from app.routers import staff as staff_router
from app.routers import dashboard as dashboard_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router.router)
    app.include_router(hotels_router.router, prefix="/api/v1")
    app.include_router(hotels_router.branches_router, prefix="/api/v1")
    app.include_router(bookings_router.router, prefix="/api/v1")
    app.include_router(restaurant_router.router, prefix="/api/v1")
    app.include_router(staff_router.router, prefix="/api/v1")
    app.include_router(dashboard_router.router, prefix="/api/v1")

    return app


app = create_app()
