import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import get_current_user
from app.core.dependencies import get_redis
from app.db.session import get_db
from app.schemas.dashboard import DailyOccupancy, DailyRevenue, DashboardSummary
from app.services.dashboard import DashboardService

# Read-only aggregate views - all roles plausibly want dashboard visibility.
# TODO: scope_branch() (app/core/auth_dependencies.py) is NOT yet wired into the
# query logic here - every authenticated role can currently request any branch_id.
# Wiring real branch scoping requires deeper service/repo changes; deferred to a later phase.
router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(get_current_user)])


def get_dashboard_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> DashboardService:
    return DashboardService(db, redis)


ServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(branch_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_summary(branch_id)


@router.get("/occupancy", response_model=list[DailyOccupancy])
async def get_occupancy_trend(branch_id: uuid.UUID, svc: ServiceDep, days: int = 30):
    return await svc.get_occupancy_trend(branch_id, days)


@router.get("/revenue", response_model=list[DailyRevenue])
async def get_revenue_trend(branch_id: uuid.UUID, svc: ServiceDep, days: int = 30):
    return await svc.get_revenue_trend(branch_id, days)
