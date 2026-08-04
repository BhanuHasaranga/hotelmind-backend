import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from app.models.recommendation import Recommendation
from app.repositories.recommendation import (
    MlRoomTypeMappingRepository,
    PricingGuardrailRepository,
    RecommendationRepository,
    StaffingGuardrailRepository,
)


class RecommendationService:
    def __init__(
        self,
        recommendation_repo: RecommendationRepository,
        pricing_guardrail_repo: PricingGuardrailRepository,
        staffing_guardrail_repo: StaffingGuardrailRepository,
        ml_room_type_mapping_repo: MlRoomTypeMappingRepository,
    ) -> None:
        self.recommendation_repo = recommendation_repo
        self.pricing_guardrail_repo = pricing_guardrail_repo
        self.staffing_guardrail_repo = staffing_guardrail_repo
        self.ml_room_type_mapping_repo = ml_room_type_mapping_repo

    async def get_ml_room_type_id(self, room_type_id: uuid.UUID) -> int:
        ml_id = await self.ml_room_type_mapping_repo.get_ml_id_for(room_type_id)
        if ml_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This room type has no ML mapping yet — an OWNER or OPS_MANAGER "
                    "must map it via PUT /ml/room-type-mappings before pricing/occupancy "
                    "predictions can run for it."
                ),
            )
        return ml_id

    async def record_shown(
        self,
        branch_id: uuid.UUID,
        type_: str,
        entity_ref: str | None,
        payload: dict,
        shown_to_user_id: uuid.UUID,
    ) -> Recommendation:
        return await self.recommendation_repo.create(
            {
                "branch_id": branch_id,
                "type": type_,
                "entity_ref": entity_ref,
                "payload": payload,
                "shown_to_user_id": shown_to_user_id,
                "shown_at": datetime.now(timezone.utc),
                "status": "SHOWN",
            }
        )

    async def clamp_price(
        self, branch_id: uuid.UUID, room_type_id: uuid.UUID, recommended_price: float
    ) -> tuple[float, bool]:
        guardrail = await self.pricing_guardrail_repo.get_active_for(branch_id, room_type_id)
        if guardrail is None:
            return recommended_price, False

        price = Decimal(str(recommended_price))
        clamped = max(guardrail.min_price, min(guardrail.max_price, price))
        return float(clamped), clamped != price

    async def act_on_recommendation(
        self, recommendation_id: uuid.UUID, status_: str, applied_value: dict | None
    ) -> Recommendation:
        if status_ not in ("ACCEPTED", "MODIFIED", "DISMISSED"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

        recommendation = await self.recommendation_repo.get(recommendation_id)
        if recommendation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

        return await self.recommendation_repo.update(
            recommendation,
            {
                "status": status_,
                "action_taken_at": datetime.now(timezone.utc),
                "applied_value": applied_value,
            },
        )

    async def measure_outcome(self, recommendation_id: uuid.UUID, outcome_value: dict, outcome_delta: Decimal) -> Recommendation:
        recommendation = await self.recommendation_repo.get(recommendation_id)
        if recommendation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

        return await self.recommendation_repo.update(
            recommendation,
            {
                "outcome_measured_at": datetime.now(timezone.utc),
                "outcome_value": outcome_value,
                "outcome_delta": outcome_delta,
            },
        )
