import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import get_current_user, require_roles, scope_branch
from app.core.dependencies import get_redis
from app.db.session import get_db
from app.models.user import User
from app.repositories.hotel import RoomTypeRepository
from app.repositories.recommendation import (
    MlRoomTypeMappingRepository,
    PricingGuardrailRepository,
    RecommendationRepository,
    StaffingGuardrailRepository,
)
from app.schemas.ml import (
    MeasureOutcomeResponse,
    PricingGuardrailIn,
    PricingGuardrailOut,
    RecommendationActionRequest,
    RecommendationOut,
    StaffingGuardrailIn,
    StaffingGuardrailOut,
)
from app.services.dashboard import DashboardService
from app.services.recommendation import RecommendationService

router = APIRouter(tags=["Recommendations"], dependencies=[Depends(get_current_user)])


def get_recommendation_service(db: AsyncSession = Depends(get_db)) -> RecommendationService:
    return RecommendationService(
        recommendation_repo=RecommendationRepository(db),
        pricing_guardrail_repo=PricingGuardrailRepository(db),
        staffing_guardrail_repo=StaffingGuardrailRepository(db),
        ml_room_type_mapping_repo=MlRoomTypeMappingRepository(db),
    )


def get_dashboard_service(db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)) -> DashboardService:
    return DashboardService(db, redis)


RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/recommendations", response_model=list[RecommendationOut])
async def list_recommendations(
    svc: RecommendationServiceDep,
    branch_id: uuid.UUID = Query(...),
    type: str | None = None,
    status_: str | None = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    scope_branch(current_user, branch_id)
    return await svc.recommendation_repo.list_by_branch(branch_id, type, status_, skip, limit)


@router.post("/recommendations/{recommendation_id}/action", response_model=RecommendationOut)
async def act_on_recommendation(
    recommendation_id: uuid.UUID,
    payload: RecommendationActionRequest,
    svc: RecommendationServiceDep,
    current_user: User = Depends(get_current_user),
):
    recommendation = await svc.recommendation_repo.get(recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    scope_branch(current_user, recommendation.branch_id)

    updated = await svc.act_on_recommendation(recommendation_id, payload.status, payload.applied_value)

    if updated.type == "PRICING" and updated.status in ("ACCEPTED", "MODIFIED"):
        await _apply_pricing_recommendation(updated, svc)

    return updated


async def _apply_pricing_recommendation(recommendation, svc: RecommendationService) -> None:
    """Writes the accepted/modified price onto RoomType.base_price.

    applied_value takes precedence (a MODIFIED recommendation carries the
    user's edited number); ACCEPTED falls back to the clamped ML price
    recorded in payload at show-time.
    """
    room_type_id = uuid.UUID(recommendation.entity_ref)
    price = None
    if recommendation.applied_value and "price" in recommendation.applied_value:
        price = Decimal(str(recommendation.applied_value["price"]))
    elif "clamped_price" in recommendation.payload:
        price = Decimal(str(recommendation.payload["clamped_price"]))

    if price is None:
        return

    room_type_repo = RoomTypeRepository(svc.recommendation_repo.db)
    room_type = await room_type_repo.get(room_type_id)
    if room_type is not None:
        await room_type_repo.update(room_type, {"base_price": price})


@router.post("/recommendations/{recommendation_id}/measure-outcome", response_model=MeasureOutcomeResponse)
async def measure_outcome(
    recommendation_id: uuid.UUID,
    svc: RecommendationServiceDep,
    dashboard_svc: DashboardServiceDep,
    current_user: User = Depends(get_current_user),
):
    recommendation = await svc.recommendation_repo.get(recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    scope_branch(current_user, recommendation.branch_id)

    if recommendation.type != "PRICING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outcome measurement is currently only implemented for PRICING recommendations",
        )

    actual_revenue = await dashboard_svc._reservation_revenue(recommendation.branch_id, date.today(), date.today())
    predicted_revenue = Decimal(str(recommendation.payload.get("expected_revenue", 0)))
    outcome_delta = actual_revenue - predicted_revenue

    updated = await svc.measure_outcome(
        recommendation_id,
        outcome_value={"actual_revenue": float(actual_revenue)},
        outcome_delta=outcome_delta,
    )

    return MeasureOutcomeResponse(
        recommendation_id=updated.id,
        outcome_value=updated.outcome_value,
        outcome_delta=updated.outcome_delta,
    )


@router.get("/guardrails/pricing", response_model=list[PricingGuardrailOut])
async def list_pricing_guardrails(
    svc: RecommendationServiceDep,
    branch_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
):
    scope_branch(current_user, branch_id)
    return await svc.pricing_guardrail_repo.list_by_branch(branch_id)


@router.put("/guardrails/pricing", response_model=PricingGuardrailOut)
async def upsert_pricing_guardrail(
    payload: PricingGuardrailIn,
    svc: RecommendationServiceDep,
    current_user: User = Depends(require_roles("OWNER", "REVENUE_MANAGER")),
):
    scope_branch(current_user, payload.branch_id)
    existing = await svc.pricing_guardrail_repo.get_active_for(payload.branch_id, payload.room_type_id)

    data = {
        "branch_id": payload.branch_id,
        "room_type_id": payload.room_type_id,
        "min_price": payload.min_price,
        "max_price": payload.max_price,
        "max_daily_change_pct": payload.max_daily_change_pct,
        "updated_by_user_id": current_user.id,
    }

    if existing is not None:
        return await svc.pricing_guardrail_repo.update(existing, data)
    return await svc.pricing_guardrail_repo.create(data)


@router.get("/guardrails/staffing", response_model=list[StaffingGuardrailOut])
async def list_staffing_guardrails(
    svc: RecommendationServiceDep,
    branch_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
):
    scope_branch(current_user, branch_id)
    return await svc.staffing_guardrail_repo.list_by_branch(branch_id)


@router.put("/guardrails/staffing", response_model=StaffingGuardrailOut)
async def upsert_staffing_guardrail(
    payload: StaffingGuardrailIn,
    svc: RecommendationServiceDep,
    current_user: User = Depends(require_roles("OWNER", "OPS_MANAGER")),
):
    scope_branch(current_user, payload.branch_id)
    existing = await svc.staffing_guardrail_repo.get_for_department(payload.branch_id, payload.department_id)

    data = {
        "branch_id": payload.branch_id,
        "department_id": payload.department_id,
        "min_headcount": payload.min_headcount,
        "max_headcount": payload.max_headcount,
        "updated_by_user_id": current_user.id,
    }

    if existing is not None:
        return await svc.staffing_guardrail_repo.update(existing, data)
    return await svc.staffing_guardrail_repo.create(data)
