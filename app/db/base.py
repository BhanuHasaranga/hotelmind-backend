import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    """Shared declarative base with auto timestamp columns."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ── Import all models here so Alembic autogenerate detects them ───────────────
# Uncomment each block as the domain is implemented.

from app.models.hotel import Hotel, Branch, Floor, RoomType, Room, Amenity, RoomTypeAmenity  # noqa: E402, F401
from app.models.booking import Guest, Reservation, OccupancySnapshot  # noqa: E402, F401
from app.models.restaurant import FoodCategory, MenuItem, RestaurantTable, RestaurantOrder, OrderItem  # noqa: E402, F401
from app.models.staff import Department, Employee, Schedule, Attendance  # noqa: E402, F401
