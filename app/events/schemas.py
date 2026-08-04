import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BaseEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    aggregate_type: str
    aggregate_id: str
    version: int = 1
    timestamp: datetime = Field(default_factory=_now)
    source: str = Field(default_factory=lambda: settings.EVENT_SOURCE)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    correlation_id: uuid.UUID | None = None


# ── Booking payloads ────────────────────────────────────────────────────────

class ReservationCreated(BaseModel):
    reservation_id: uuid.UUID
    room_id: uuid.UUID
    guest_id: uuid.UUID
    check_in_date: date
    check_out_date: date
    status: str
    total_amount: Decimal


class ReservationConfirmed(BaseModel):
    reservation_id: uuid.UUID
    status: str


class ReservationCancelled(BaseModel):
    reservation_id: uuid.UUID
    status: str
    cancellation_reason: str | None = None


class ReservationCheckedIn(BaseModel):
    reservation_id: uuid.UUID
    room_id: uuid.UUID
    status: str


class ReservationCheckedOut(BaseModel):
    reservation_id: uuid.UUID
    room_id: uuid.UUID
    status: str


class ReservationUpdated(BaseModel):
    reservation_id: uuid.UUID
    status: str
    changes: dict[str, Any] = Field(default_factory=dict)


# ── Restaurant payloads ─────────────────────────────────────────────────────

class OrderCreated(BaseModel):
    order_id: uuid.UUID
    branch_id: uuid.UUID
    status: str
    total_amount: Decimal


class OrderUpdated(BaseModel):
    order_id: uuid.UUID
    status: str
    changes: dict[str, Any] = Field(default_factory=dict)


class OrderCompleted(BaseModel):
    order_id: uuid.UUID
    status: str
    total_amount: Decimal


class OrderCancelled(BaseModel):
    order_id: uuid.UUID
    status: str


# ── Payment payloads ─────────────────────────────────────────────────────────

class PaymentCompleted(BaseModel):
    payment_id: uuid.UUID
    reservation_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    amount: Decimal
    method: str
    status: str


class RefundIssued(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal
    reason: str | None = None
    status: str


# ── Review payloads ──────────────────────────────────────────────────────────

class ReviewCreated(BaseModel):
    review_id: uuid.UUID
    reservation_id: uuid.UUID | None = None
    guest_id: uuid.UUID | None = None
    rating: int
    comment: str | None = None


class SentimentCalculated(BaseModel):
    review_id: uuid.UUID
    sentiment: str
    sentiment_score: float


# ── ML payloads ──────────────────────────────────────────────────────────────

class OccupancyForecastReady(BaseModel):
    branch_id: uuid.UUID
    forecast_date: date
    predicted_occupancy_pct: float


class PriceRecommendationReady(BaseModel):
    room_id: uuid.UUID
    recommended_price: Decimal
    valid_from: date


class RestaurantForecastReady(BaseModel):
    branch_id: uuid.UUID
    forecast_date: date
    predicted_sales: Decimal


class StaffForecastReady(BaseModel):
    branch_id: uuid.UUID
    forecast_date: date
    predicted_staff_needed: int


class ChurnPredictionReady(BaseModel):
    guest_id: uuid.UUID
    churn_probability: float


class AIInsightGenerated(BaseModel):
    insight_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    category: str
    summary: str


# ── Dashboard payloads ───────────────────────────────────────────────────────

class OccupancyChanged(BaseModel):
    branch_id: uuid.UUID
    occupancy_pct: float


class RevenueChanged(BaseModel):
    branch_id: uuid.UUID | None = None
    total_revenue: Decimal


class BookingCountChanged(BaseModel):
    branch_id: uuid.UUID | None = None
    booking_count: int


class RestaurantSalesChanged(BaseModel):
    branch_id: uuid.UUID | None = None
    total_sales: Decimal


class ForecastUpdated(BaseModel):
    branch_id: uuid.UUID | None = None
    forecast_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class AIInsightUpdated(BaseModel):
    insight_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    category: str
    summary: str
