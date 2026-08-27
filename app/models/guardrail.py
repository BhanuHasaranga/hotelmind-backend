import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PricingGuardrail(Base):
    __tablename__ = "pricing_guardrails"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    # Null room_type_id means "applies to every room type on this branch".
    room_type_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("room_types.id"), nullable=True)
    min_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_daily_change_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("25.00"))
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class StaffingGuardrail(Base):
    __tablename__ = "staffing_guardrails"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    min_headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_headcount: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class MlRoomTypeMapping(Base):
    """Maps a real RoomType (UUID, backend) to the ML service's synthetic
    room_type_id (small int, indexes a static parquet dim table today).

    branch_id needs no equivalent mapping: every ML prediction endpoint
    treats branch_id as an opaque pass-through value it echoes back but never
    looks up (see hotelmind-ml/src/prediction/predict_*.py) - only
    room_type_id is actually used to join against ML's room_type_dim.
    """

    __tablename__ = "ml_room_type_mappings"

    room_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    ml_room_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
