import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"), nullable=True)
    guest_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("guests.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    # POSITIVE | NEGATIVE | NEUTRAL - filled in once sentiment scoring runs
    sentiment: Mapped[str | None] = mapped_column(String(20))
    sentiment_score: Mapped[float | None] = mapped_column(Float)
