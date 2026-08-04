import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"), nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("restaurant_orders.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # CARD | CASH | ONLINE | BANK_TRANSFER
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    # PENDING | COMPLETED | REFUNDED | FAILED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    refund_reason: Mapped[str | None] = mapped_column(Text)
