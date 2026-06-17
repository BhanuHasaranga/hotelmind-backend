import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Reservation
from app.models.hotel import Floor, Room
from app.models.restaurant import RestaurantOrder
from app.schemas.dashboard import DailyOccupancy, DailyRevenue, DashboardSummary


class DashboardService:
    """Aggregation queries — uses raw SQL expressions for performance."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, branch_id: uuid.UUID) -> DashboardSummary:
        today = date.today()
        month_start = today.replace(day=1)

        # ── Occupancy ─────────────────────────────────────────────────────────
        total_rooms, occupied_rooms = await self._room_counts(branch_id)
        occupancy_pct = (occupied_rooms / total_rooms * 100) if total_rooms else 0.0

        # ── Revenue ───────────────────────────────────────────────────────────
        revenue_today = await self._reservation_revenue(branch_id, today, today)
        revenue_mtd = await self._reservation_revenue(branch_id, month_start, today)

        # ── Reservations ──────────────────────────────────────────────────────
        res_today = await self._reservation_count(branch_id, today)
        res_pending = await self._reservation_count_by_status(branch_id, "PENDING")

        # ── Restaurant ────────────────────────────────────────────────────────
        restaurant_sales = await self._restaurant_sales(branch_id, today)
        orders_open = await self._open_orders_count(branch_id)

        return DashboardSummary(
            occupancy_pct=round(occupancy_pct, 2),
            occupied_rooms=occupied_rooms,
            total_rooms=total_rooms,
            revenue_today=revenue_today,
            revenue_mtd=revenue_mtd,
            reservations_today=res_today,
            reservations_pending=res_pending,
            restaurant_sales_today=restaurant_sales,
            restaurant_orders_open=orders_open,
        )

    async def get_occupancy_trend(self, branch_id: uuid.UUID, days: int) -> list[DailyOccupancy]:
        """Returns per-day occupancy for last N days from live reservation data."""
        today = date.today()
        result = []
        total_rooms, _ = await self._room_counts(branch_id)
        for delta in range(days - 1, -1, -1):
            d = today - timedelta(days=delta)
            occupied = await self._occupied_on_date(branch_id, d)
            pct = (occupied / total_rooms * 100) if total_rooms else 0.0
            result.append(DailyOccupancy(
                date=d.isoformat(),
                occupancy_pct=round(pct, 2),
                occupied_rooms=occupied,
                total_rooms=total_rooms,
            ))
        return result

    async def get_revenue_trend(self, branch_id: uuid.UUID, days: int) -> list[DailyRevenue]:
        today = date.today()
        result = []
        for delta in range(days - 1, -1, -1):
            d = today - timedelta(days=delta)
            rev = await self._reservation_revenue(branch_id, d, d)
            result.append(DailyRevenue(date=d.isoformat(), revenue=rev))
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _room_counts(self, branch_id: uuid.UUID) -> tuple[int, int]:
        total_r = await self.db.execute(
            select(func.count(Room.id))
            .join(Floor, Room.floor_id == Floor.id)
            .where(Floor.branch_id == branch_id, Room.is_active == True)  # noqa: E712
        )
        occ_r = await self.db.execute(
            select(func.count(Room.id))
            .join(Floor, Room.floor_id == Floor.id)
            .where(Floor.branch_id == branch_id, Room.status == "OCCUPIED", Room.is_active == True)  # noqa: E712
        )
        return total_r.scalar_one() or 0, occ_r.scalar_one() or 0

    async def _reservation_revenue(self, branch_id: uuid.UUID, from_date: date, to_date: date) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Reservation.total_amount), 0))
            .join(Room, Reservation.room_id == Room.id)
            .join(Floor, Room.floor_id == Floor.id)
            .where(
                Floor.branch_id == branch_id,
                Reservation.check_in_date >= from_date,
                Reservation.check_in_date <= to_date,
                Reservation.status.not_in(("CANCELLED", "NO_SHOW")),
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def _reservation_count(self, branch_id: uuid.UUID, on_date: date) -> int:
        result = await self.db.execute(
            select(func.count(Reservation.id))
            .join(Room, Reservation.room_id == Room.id)
            .join(Floor, Room.floor_id == Floor.id)
            .where(
                Floor.branch_id == branch_id,
                Reservation.check_in_date == on_date,
                Reservation.status.not_in(("CANCELLED", "NO_SHOW")),
            )
        )
        return result.scalar_one() or 0

    async def _reservation_count_by_status(self, branch_id: uuid.UUID, res_status: str) -> int:
        result = await self.db.execute(
            select(func.count(Reservation.id))
            .join(Room, Reservation.room_id == Room.id)
            .join(Floor, Room.floor_id == Floor.id)
            .where(Floor.branch_id == branch_id, Reservation.status == res_status)
        )
        return result.scalar_one() or 0

    async def _occupied_on_date(self, branch_id: uuid.UUID, on_date: date) -> int:
        result = await self.db.execute(
            select(func.count(Reservation.id))
            .join(Room, Reservation.room_id == Room.id)
            .join(Floor, Room.floor_id == Floor.id)
            .where(
                Floor.branch_id == branch_id,
                Reservation.check_in_date <= on_date,
                Reservation.check_out_date > on_date,
                Reservation.status.not_in(("CANCELLED", "NO_SHOW")),
            )
        )
        return result.scalar_one() or 0

    async def _restaurant_sales(self, branch_id: uuid.UUID, on_date: date) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(RestaurantOrder.total_amount), 0))
            .where(
                RestaurantOrder.branch_id == branch_id,
                RestaurantOrder.status == "CLOSED",
                func.date(RestaurantOrder.closed_at) == on_date,
            )
        )
        return Decimal(str(result.scalar_one() or 0))

    async def _open_orders_count(self, branch_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(RestaurantOrder.id))
            .where(RestaurantOrder.branch_id == branch_id, RestaurantOrder.status == "OPEN")
        )
        return result.scalar_one() or 0
