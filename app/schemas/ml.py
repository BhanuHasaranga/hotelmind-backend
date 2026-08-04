import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ModelMeta(BaseModel):
    model_version: int | str
    trained_at: str
    mlflow_experiment_id: str | None = None
    latency_ms: float
    confidence: float | None = None


# ── Pricing ──────────────────────────────────────────────────────────────────

class PricingRecommendRequest(BaseModel):
    branch_id: uuid.UUID
    room_type_id: uuid.UUID
    date: str
    current_occupancy_pct: float
    current_revenue: float
    revenue_7day_avg: float
    total_rooms: int


class PricingRecommendResponse(BaseModel):
    recommendation_id: uuid.UUID
    branch_id: uuid.UUID
    room_type_id: uuid.UUID
    date: str
    recommended_price: float
    expected_revenue: float
    guardrail_clamped: bool
    meta: ModelMeta | None = None


# ── Occupancy ────────────────────────────────────────────────────────────────

class OccupancyForecastRequest(BaseModel):
    branch_id: uuid.UUID
    horizon_days: int | None = None


class OccupancyDayForecast(BaseModel):
    date: str
    predicted_occupancy_pct: float
    ci_lower: float
    ci_upper: float
    model_used: str


class OccupancyForecastResponse(BaseModel):
    branch_id: uuid.UUID
    forecast: list[OccupancyDayForecast]
    meta: ModelMeta | None = None


# ── Restaurant demand ────────────────────────────────────────────────────────

class RestaurantDemandRequest(BaseModel):
    branch_id: uuid.UUID
    date: str
    recent_total_orders_lag_1: float
    recent_total_orders_lag_7: float
    recent_total_orders_rolling_mean_7: float
    avg_item_value: float


class MealForecast(BaseModel):
    expected_quantity: float
    expected_revenue: float


class RestaurantDemandResponse(BaseModel):
    recommendation_id: uuid.UUID
    branch_id: uuid.UUID
    date: str
    breakfast: MealForecast
    lunch: MealForecast
    dinner: MealForecast
    meta: ModelMeta | None = None


# ── Staffing ─────────────────────────────────────────────────────────────────

class StaffRequirementRequest(BaseModel):
    branch_id: uuid.UUID
    department: str
    date: str
    scheduled_employees: int
    present_employees_lag_7: float
    present_employees_rolling_mean_7: float


class StaffRequirementResponse(BaseModel):
    recommendation_id: uuid.UUID
    branch_id: uuid.UUID
    department: str
    date: str
    required_staff: int
    confidence_note: str
    meta: ModelMeta | None = None


# ── Churn ────────────────────────────────────────────────────────────────────

class ChurnPredictRequest(BaseModel):
    guest_id: uuid.UUID


class ChurnPredictResponse(BaseModel):
    recommendation_id: uuid.UUID | None
    guest_id: uuid.UUID
    churn_probability: float | None
    risk_level: str
    model_used: str
    note: str | None = None
    meta: ModelMeta | None = None


# ── RAG assistant ────────────────────────────────────────────────────────────

class RagQueryRequest(BaseModel):
    query: str
    persona: str = "hotel_analyst"
    session_id: str | None = None
    branch_id: uuid.UUID | None = None


class RagCitation(BaseModel):
    source: str
    doc_type: str | None = None
    score: float = 0.0


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[RagCitation]
    used_llm: bool


# ── Recommendations (closed-loop) ───────────────────────────────────────────

class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    type: str
    entity_ref: str | None
    payload: dict
    shown_to_user_id: uuid.UUID
    shown_at: datetime
    status: str
    action_taken_at: datetime | None
    applied_value: dict | None
    outcome_measured_at: datetime | None
    outcome_value: dict | None
    outcome_delta: Decimal | None


class RecommendationActionRequest(BaseModel):
    status: str  # ACCEPTED | MODIFIED | DISMISSED
    applied_value: dict | None = None


class MeasureOutcomeResponse(BaseModel):
    recommendation_id: uuid.UUID
    outcome_value: dict
    outcome_delta: Decimal


class PricingGuardrailIn(BaseModel):
    branch_id: uuid.UUID
    room_type_id: uuid.UUID | None = None
    min_price: Decimal
    max_price: Decimal
    max_daily_change_pct: Decimal = Decimal("25.00")


class PricingGuardrailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    room_type_id: uuid.UUID | None
    min_price: Decimal
    max_price: Decimal
    max_daily_change_pct: Decimal


class StaffingGuardrailIn(BaseModel):
    branch_id: uuid.UUID
    department_id: uuid.UUID
    min_headcount: int = 1
    max_headcount: int


class StaffingGuardrailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    department_id: uuid.UUID
    min_headcount: int
    max_headcount: int
