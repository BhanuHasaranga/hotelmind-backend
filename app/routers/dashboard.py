import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.dashboard import DailyOccupancy, DailyRevenue, DashboardSummary
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


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
