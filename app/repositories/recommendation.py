import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardrail import MlRoomTypeMapping, PricingGuardrail, StaffingGuardrail
from app.models.recommendation import Recommendation
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Recommendation, db)

    async def list_by_branch(
        self,
        branch_id: uuid.UUID,
        type_: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Recommendation]:
        stmt = select(Recommendation).where(Recommendation.branch_id == branch_id)
        if type_ is not None:
            stmt = stmt.where(Recommendation.type == type_)
        if status is not None:
            stmt = stmt.where(Recommendation.status == status)
        stmt = stmt.order_by(Recommendation.shown_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class PricingGuardrailRepository(BaseRepository[PricingGuardrail]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(PricingGuardrail, db)

    async def get_active_for(
        self, branch_id: uuid.UUID, room_type_id: uuid.UUID
    ) -> PricingGuardrail | None:
        # Prefer a room-type-specific guardrail; fall back to a branch-wide one.
        specific = await self.db.execute(
            select(PricingGuardrail).where(
                PricingGuardrail.branch_id == branch_id,
                PricingGuardrail.room_type_id == room_type_id,
            )
        )
        found = specific.scalar_one_or_none()
        if found is not None:
            return found

        branch_wide = await self.db.execute(
            select(PricingGuardrail).where(
                PricingGuardrail.branch_id == branch_id,
                PricingGuardrail.room_type_id.is_(None),
            )
        )
        return branch_wide.scalar_one_or_none()

    async def list_by_branch(self, branch_id: uuid.UUID) -> list[PricingGuardrail]:
        result = await self.db.execute(select(PricingGuardrail).where(PricingGuardrail.branch_id == branch_id))
        return list(result.scalars().all())


class StaffingGuardrailRepository(BaseRepository[StaffingGuardrail]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(StaffingGuardrail, db)

    async def get_for_department(
        self, branch_id: uuid.UUID, department_id: uuid.UUID
    ) -> StaffingGuardrail | None:
        result = await self.db.execute(
            select(StaffingGuardrail).where(
                StaffingGuardrail.branch_id == branch_id,
                StaffingGuardrail.department_id == department_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_branch(self, branch_id: uuid.UUID) -> list[StaffingGuardrail]:
        result = await self.db.execute(select(StaffingGuardrail).where(StaffingGuardrail.branch_id == branch_id))
        return list(result.scalars().all())


class MlRoomTypeMappingRepository(BaseRepository[MlRoomTypeMapping]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(MlRoomTypeMapping, db)

    async def get_ml_id_for(self, room_type_id: uuid.UUID) -> int | None:
        result = await self.db.execute(
            select(MlRoomTypeMapping.ml_room_type_id).where(MlRoomTypeMapping.room_type_id == room_type_id)
        )
        return result.scalar_one_or_none()
