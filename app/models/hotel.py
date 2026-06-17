import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.booking import Reservation
    from app.models.restaurant import FoodCategory, RestaurantTable, RestaurantOrder
    from app.models.staff import Department


# ── Junction table (many-to-many: room_types ↔ amenities) ────────────────────
RoomTypeAmenity = Table(
    "room_type_amenities",
    Base.metadata,
    Column("room_type_id", ForeignKey("room_types.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True),
)


class Hotel(Base):
    __tablename__ = "hotels"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    star_rating: Mapped[int] = mapped_column(Integer, default=3)
    address: Mapped[str] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    branches: Mapped[list["Branch"]] = relationship("Branch", back_populates="hotel", cascade="all, delete-orphan")


class Branch(Base):
    __tablename__ = "branches"

    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    is_main_branch: Mapped[bool] = mapped_column(Boolean, default=False)

    hotel: Mapped["Hotel"] = relationship("Hotel", back_populates="branches")
    floors: Mapped[list["Floor"]] = relationship("Floor", back_populates="branch", cascade="all, delete-orphan")
    room_types: Mapped[list["RoomType"]] = relationship("RoomType", back_populates="branch", cascade="all, delete-orphan")
    departments: Mapped[list["Department"]] = relationship("Department", back_populates="branch")
    food_categories: Mapped[list["FoodCategory"]] = relationship("FoodCategory", back_populates="branch")
    restaurant_tables: Mapped[list["RestaurantTable"]] = relationship("RestaurantTable", back_populates="branch")
    restaurant_orders: Mapped[list["RestaurantOrder"]] = relationship("RestaurantOrder", back_populates="branch")


class Floor(Base):
    __tablename__ = "floors"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    floor_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))

    branch: Mapped["Branch"] = relationship("Branch", back_populates="floors")
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="floor", cascade="all, delete-orphan")


class RoomType(Base):
    __tablename__ = "room_types"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    # e.g. STANDARD, DELUXE, SUITE, PRESIDENTIAL
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_occupancy: Mapped[int] = mapped_column(Integer, default=2)
    description: Mapped[str | None] = mapped_column(String(500))

    branch: Mapped["Branch"] = relationship("Branch", back_populates="room_types")
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="room_type")
    amenities: Mapped[list["Amenity"]] = relationship("Amenity", secondary=RoomTypeAmenity, back_populates="room_types")


class Room(Base):
    __tablename__ = "rooms"

    floor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("floors.id", ondelete="CASCADE"), nullable=False)
    room_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("room_types.id"), nullable=False)
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    # AVAILABLE | OCCUPIED | MAINTENANCE | CLEANING
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    floor: Mapped["Floor"] = relationship("Floor", back_populates="rooms")
    room_type: Mapped["RoomType"] = relationship("RoomType", back_populates="rooms")
    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="room")


class Amenity(Base):
    __tablename__ = "amenities"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icon: Mapped[str | None] = mapped_column(String(50))  # icon name / emoji

    room_types: Mapped[list["RoomType"]] = relationship("RoomType", secondary=RoomTypeAmenity, back_populates="amenities")
