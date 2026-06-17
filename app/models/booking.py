import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.hotel import Room, Branch


class Guest(Base):
    __tablename__ = "guests"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    id_type: Mapped[str | None] = mapped_column(String(50))   # PASSPORT | NIC | DRIVING_LICENSE
    id_number: Mapped[str | None] = mapped_column(String(100))
    nationality: Mapped[str | None] = mapped_column(String(100))

    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="guest")


class Reservation(Base):
    __tablename__ = "reservations"

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    guest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guests.id"), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    # State machine: PENDING → CONFIRMED → CHECKED_IN → CHECKED_OUT | CANCELLED | NO_SHOW
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    adults: Mapped[int] = mapped_column(Integer, default=1)
    children: Mapped[int] = mapped_column(Integer, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    special_requests: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    room: Mapped["Room"] = relationship("Room", back_populates="reservations")
    guest: Mapped["Guest"] = relationship("Guest", back_populates="reservations")


class OccupancySnapshot(Base):
    """Daily occupancy snapshot per branch — written on check-in/check-out."""
    __tablename__ = "occupancy_snapshots"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    occupied_rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    occupancy_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
