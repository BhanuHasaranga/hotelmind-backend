import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Guest, Reservation
from app.repositories.base import BaseRepository


class GuestRepository(BaseRepository[Guest]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Guest, db)

    async def get_by_email(self, email: str) -> Guest | None:
        result = await self.db.execute(select(Guest).where(Guest.email == email))
        return result.scalar_one_or_none()

    async def get_with_reservations(self, guest_id: uuid.UUID) -> Guest | None:
        result = await self.db.execute(
            select(Guest)
            .options(selectinload(Guest.reservations))
            .where(Guest.id == guest_id)
        )
        return result.scalar_one_or_none()


class ReservationRepository(BaseRepository[Reservation]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Reservation, db)

    async def has_conflict(
        self,
        room_id: uuid.UUID,
        check_in: date,
        check_out: date,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Returns True if a date-overlapping active reservation exists for the room."""
        terminal_statuses = ("CANCELLED", "NO_SHOW")
        query = select(Reservation.id).where(
            and_(
                Reservation.room_id == room_id,
                Reservation.status.not_in(terminal_statuses),
                Reservation.check_in_date < check_out,
                Reservation.check_out_date > check_in,
            )
        )
        if exclude_id:
            query = query.where(Reservation.id != exclude_id)
        result = await self.db.execute(query)
        return result.first() is not None

    async def filter(
        self,
        branch_id: uuid.UUID | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Reservation]:
        query = (
            select(Reservation)
            .options(selectinload(Reservation.guest))
            .offset(skip)
            .limit(limit)
        )
        if status:
            query = query.where(Reservation.status == status)
        if date_from:
            query = query.where(Reservation.check_in_date >= date_from)
        if date_to:
            query = query.where(Reservation.check_out_date <= date_to)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_with_guest(self, reservation_id: uuid.UUID) -> Reservation | None:
        result = await self.db.execute(
            select(Reservation)
            .options(selectinload(Reservation.guest))
            .where(Reservation.id == reservation_id)
        )
        return result.scalar_one_or_none()
