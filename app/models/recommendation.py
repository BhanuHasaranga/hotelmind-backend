import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Recommendation(Base):
    """A single ML suggestion shown to a user, and what happened to it.

    One generic table (rather than a typed table per `type`) trades some
    column-level type-safety for far less schema/repo boilerplate - every
    recommendation type shares the same shown -> acted-on -> outcome-measured
    lifecycle, so the JSONB payload/outcome columns hold the type-specific
    shape while the lifecycle columns stay uniform and queryable across types
    for the history/outcome UI.
    """

    __tablename__ = "recommendations"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    # PRICING | STAFFING | RESTAURANT_DEMAND | CHURN_INTERVENTION
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Free-form reference to the thing this recommendation is about
    # (e.g. a room_type_id, a department name, a guest_id) - shape depends on `type`.
    entity_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Raw ML response, including its ModelMeta (version/confidence/etc).
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    shown_to_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # SHOWN | ACCEPTED | MODIFIED | DISMISSED
    status: Mapped[str] = mapped_column(String(20), default="SHOWN", nullable=False)
    action_taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # What was actually applied to the system - equal to the ML suggestion for
    # ACCEPTED, the user's edited value for MODIFIED, null for DISMISSED/SHOWN.
    applied_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    outcome_measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # The headline "did this help" number - e.g. actual revenue minus the
    # revenue the ML response predicted. Null until measured.
    outcome_delta: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
