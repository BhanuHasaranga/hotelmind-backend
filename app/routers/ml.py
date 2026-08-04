import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import get_current_user, require_roles, scope_branch
from app.core.dependencies import get_redis
from app.db.session import get_db
from app.models.guardrail import MlRoomTypeMapping
from app.models.user import User
from app.repositories.recommendation import (
    MlRoomTypeMappingRepository,
    PricingGuardrailRepository,
    RecommendationRepository,
    StaffingGuardrailRepository,
)
from app.schemas.ml import (
    ChurnPredictRequest,
    ChurnPredictResponse,
    ModelMeta,
    OccupancyForecastRequest,
    OccupancyForecastResponse,
    PricingRecommendRequest,
    PricingRecommendResponse,
    RagQueryRequest,
    RagQueryResponse,
    RestaurantDemandRequest,
    RestaurantDemandResponse,
    StaffRequirementRequest,
    StaffRequirementResponse,
)
from app.services.dashboard import DashboardService
from app.services.ml_client import MLClient, MLServiceError
from app.services.recommendation import RecommendationService

router = APIRouter(prefix="/ml", tags=["ML"], dependencies=[Depends(get_current_user)])

# A fixed demo branch id is intentional: the ML service's branch_id is a pure
# pass-through it never looks up against real data (see
# hotelmind-ml/src/prediction/predict_*.py) — any stable integer works.
_ML_DEMO_BRANCH_ID = 1


def get_recommendation_service(db: AsyncSession = Depends(get_db)) -> RecommendationService:
    return RecommendationService(
        recommendation_repo=RecommendationRepository(db),
        pricing_guardrail_repo=PricingGuardrailRepository(db),
        staffing_guardrail_repo=StaffingGuardrailRepository(db),
        ml_room_type_mapping_repo=MlRoomTypeMappingRepository(db),
    )


def get_ml_client() -> MLClient:
    return MLClient()


def get_dashboard_service(db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)) -> DashboardService:
    return DashboardService(db, redis)


RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]
MLClientDep = Annotated[MLClient, Depends(get_ml_client)]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


def _to_model_meta(payload: dict) -> ModelMeta | None:
    meta = payload.get("meta")
    return ModelMeta(**meta) if meta else None


@router.post("/pricing/recommend", response_model=PricingRecommendResponse)
async def recommend_pricing(
    request: PricingRecommendRequest,
    svc: RecommendationServiceDep,
    ml: MLClientDep,
    current_user: User = Depends(require_roles("OWNER", "REVENUE_MANAGER")),
):
    scope_branch(current_user, request.branch_id)
    ml_room_type_id = await svc.get_ml_room_type_id(request.room_type_id)

    try:
        result = await ml.predict_pricing(
            ml_branch_id=_ML_DEMO_BRANCH_ID,
            ml_room_type_id=ml_room_type_id,
            date=request.date,
            current_occupancy_pct=request.current_occupancy_pct,
            current_revenue=request.current_revenue,
            revenue_7day_avg=request.revenue_7day_avg,
            total_rooms=request.total_rooms,
        )
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    clamped_price, was_clamped = await svc.clamp_price(
        request.branch_id, request.room_type_id, result["recommended_price"]
    )

    recommendation = await svc.record_shown(
        branch_id=request.branch_id,
        type_="PRICING",
        entity_ref=str(request.room_type_id),
        payload={**result, "guardrail_clamped": was_clamped, "clamped_price": clamped_price},
        shown_to_user_id=current_user.id,
    )

    return PricingRecommendResponse(
        recommendation_id=recommendation.id,
        branch_id=request.branch_id,
        room_type_id=request.room_type_id,
        date=request.date,
        recommended_price=clamped_price,
        expected_revenue=result["expected_revenue"],
        guardrail_clamped=was_clamped,
        meta=_to_model_meta(result),
    )


@router.post("/occupancy/forecast", response_model=OccupancyForecastResponse)
async def forecast_occupancy(
    request: OccupancyForecastRequest,
    ml: MLClientDep,
    current_user: User = Depends(get_current_user),
):
    scope_branch(current_user, request.branch_id)
    try:
        result = await ml.predict_occupancy(_ML_DEMO_BRANCH_ID, request.horizon_days)
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return OccupancyForecastResponse(
        branch_id=request.branch_id,
        forecast=result["forecast"],
        meta=_to_model_meta(result),
    )


@router.post("/restaurant/demand", response_model=RestaurantDemandResponse)
async def forecast_restaurant_demand(
    request: RestaurantDemandRequest,
    svc: RecommendationServiceDep,
    ml: MLClientDep,
    current_user: User = Depends(require_roles("OWNER", "RESTAURANT_MANAGER")),
):
    scope_branch(current_user, request.branch_id)
    try:
        result = await ml.predict_restaurant(
            ml_branch_id=_ML_DEMO_BRANCH_ID,
            date=request.date,
            recent_total_orders_lag_1=request.recent_total_orders_lag_1,
            recent_total_orders_lag_7=request.recent_total_orders_lag_7,
            recent_total_orders_rolling_mean_7=request.recent_total_orders_rolling_mean_7,
            avg_item_value=request.avg_item_value,
        )
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    recommendation = await svc.record_shown(
        branch_id=request.branch_id,
        type_="RESTAURANT_DEMAND",
        entity_ref=request.date,
        payload=result,
        shown_to_user_id=current_user.id,
    )

    return RestaurantDemandResponse(
        recommendation_id=recommendation.id,
        branch_id=request.branch_id,
        date=request.date,
        breakfast=result["breakfast"],
        lunch=result["lunch"],
        dinner=result["dinner"],
        meta=_to_model_meta(result),
    )


@router.post("/staff/requirements", response_model=StaffRequirementResponse)
async def recommend_staff_requirements(
    request: StaffRequirementRequest,
    svc: RecommendationServiceDep,
    ml: MLClientDep,
    current_user: User = Depends(require_roles("OWNER", "OPS_MANAGER")),
):
    scope_branch(current_user, request.branch_id)
    try:
        result = await ml.predict_staff(
            ml_branch_id=_ML_DEMO_BRANCH_ID,
            department=request.department,
            date=request.date,
            scheduled_employees=request.scheduled_employees,
            present_employees_lag_7=request.present_employees_lag_7,
            present_employees_rolling_mean_7=request.present_employees_rolling_mean_7,
        )
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    recommendation = await svc.record_shown(
        branch_id=request.branch_id,
        type_="STAFFING",
        entity_ref=request.department,
        payload=result,
        shown_to_user_id=current_user.id,
    )

    return StaffRequirementResponse(
        recommendation_id=recommendation.id,
        branch_id=request.branch_id,
        department=request.department,
        date=request.date,
        required_staff=result["required_staff"],
        confidence_note=result["confidence_note"],
        meta=_to_model_meta(result),
    )


@router.post("/churn/predict", response_model=ChurnPredictResponse)
async def predict_churn(
    request: ChurnPredictRequest,
    svc: RecommendationServiceDep,
    ml: MLClientDep,
    current_user: User = Depends(require_roles("OWNER", "GUEST_EXPERIENCE_MANAGER")),
):
    try:
        result = await ml.predict_churn(str(request.guest_id))
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    recommendation_id = None
    if result.get("risk_level") in ("HIGH", "MEDIUM"):
        recommendation = await svc.record_shown(
            branch_id=current_user.branch_id or uuid.uuid4(),
            type_="CHURN_INTERVENTION",
            entity_ref=str(request.guest_id),
            payload=result,
            shown_to_user_id=current_user.id,
        )
        recommendation_id = recommendation.id

    return ChurnPredictResponse(
        recommendation_id=recommendation_id,
        guest_id=request.guest_id,
        churn_probability=result.get("churn_probability"),
        risk_level=result["risk_level"],
        model_used=result["model_used"],
        note=result.get("note"),
        meta=_to_model_meta(result),
    )


@router.post("/rag/query", response_model=RagQueryResponse)
async def query_assistant(
    request: RagQueryRequest,
    ml: MLClientDep,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await ml.rag_query(request.query, request.persona, request.session_id)
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return RagQueryResponse(**result)


@router.get("/insights")
async def get_insights(
    ml: MLClientDep,
    category: str | None = None,
    min_severity: str | None = None,
    current_user: User = Depends(get_current_user),
):
    try:
        return await ml.get_insights(category, min_severity)
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/insights/executive")
async def get_executive_insights(ml: MLClientDep, current_user: User = Depends(get_current_user)):
    try:
        return await ml.get_executive_insights()
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/insights/recommendations")
async def get_insight_recommendations(ml: MLClientDep, current_user: User = Depends(get_current_user)):
    try:
        return await ml.get_insight_recommendations()
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/insights/anomalies")
async def get_anomalies(ml: MLClientDep, current_user: User = Depends(get_current_user)):
    try:
        return await ml.get_anomalies()
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/reviews/summary")
async def get_reviews_summary(ml: MLClientDep, current_user: User = Depends(get_current_user)):
    try:
        return await ml.get_reviews_summary()
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/reviews/topics")
async def get_reviews_topics(ml: MLClientDep, current_user: User = Depends(get_current_user)):
    try:
        return await ml.get_reviews_topics()
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/reviews/complaints")
async def get_reviews_complaints(ml: MLClientDep, current_user: User = Depends(get_current_user)):
    try:
        return await ml.get_reviews_complaints()
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/reviews/trends")
async def get_reviews_trends(
    ml: MLClientDep, grain: str = "weekly", current_user: User = Depends(get_current_user)
):
    try:
        return await ml.get_reviews_trends(grain)
    except MLServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.put("/room-type-mappings", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_room_type_mapping(
    room_type_id: uuid.UUID,
    ml_room_type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("OWNER", "OPS_MANAGER")),
):
    """Maps a real RoomType to the ML service's synthetic room_type_id
    (1=Standard, 2=Deluxe, 3=Suite per hotelmind-ml's room_type_dim.csv)."""
    repo = MlRoomTypeMappingRepository(db)
    existing = await repo.db.execute(
        select(MlRoomTypeMapping).where(MlRoomTypeMapping.room_type_id == room_type_id)
    )
    mapping = existing.scalar_one_or_none()
    if mapping is not None:
        await repo.update(mapping, {"ml_room_type_id": ml_room_type_id})
    else:
        await repo.create({"room_type_id": room_type_id, "ml_room_type_id": ml_room_type_id})
