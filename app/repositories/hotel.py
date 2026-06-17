import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hotel import Branch, Floor, Hotel, Room, RoomType
from app.repositories.base import BaseRepository


class HotelRepository(BaseRepository[Hotel]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Hotel, db)

    async def get_with_branches(self, hotel_id: uuid.UUID) -> Hotel | None:
        result = await self.db.execute(
            select(Hotel)
            .options(selectinload(Hotel.branches))
            .where(Hotel.id == hotel_id)
        )
        return result.scalar_one_or_none()

    async def get_all_active(self, skip: int = 0, limit: int = 100) -> Sequence[Hotel]:
        result = await self.db.execute(
            select(Hotel).where(Hotel.is_active == True).offset(skip).limit(limit)  # noqa: E712
        )
        return result.scalars().all()


class BranchRepository(BaseRepository[Branch]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Branch, db)

    async def get_by_hotel(self, hotel_id: uuid.UUID) -> Sequence[Branch]:
        result = await self.db.execute(
            select(Branch).where(Branch.hotel_id == hotel_id)
        )
        return result.scalars().all()


class RoomTypeRepository(BaseRepository[RoomType]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RoomType, db)

    async def get_by_branch(self, branch_id: uuid.UUID) -> Sequence[RoomType]:
        result = await self.db.execute(
            select(RoomType)
            .options(selectinload(RoomType.amenities))
            .where(RoomType.branch_id == branch_id)
        )
        return result.scalars().all()


class FloorRepository(BaseRepository[Floor]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Floor, db)

    async def get_by_branch(self, branch_id: uuid.UUID) -> Sequence[Floor]:
        result = await self.db.execute(
            select(Floor).where(Floor.branch_id == branch_id)
        )
        return result.scalars().all()


class RoomRepository(BaseRepository[Room]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Room, db)

    async def get_by_branch(self, branch_id: uuid.UUID, status: str | None = None) -> Sequence[Room]:
        query = (
            select(Room)
            .join(Floor)
            .where(Floor.branch_id == branch_id)
            .options(selectinload(Room.room_type))
        )
        if status:
            query = query.where(Room.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_branch(self, branch_id: uuid.UUID) -> tuple[int, int]:
        """Returns (total_active_rooms, occupied_rooms)."""
        from sqlalchemy import func
        total_result = await self.db.execute(
            select(func.count(Room.id))
            .join(Floor)
            .where(Floor.branch_id == branch_id, Room.is_active == True)  # noqa: E712
        )
        occupied_result = await self.db.execute(
            select(func.count(Room.id))
            .join(Floor)
            .where(Floor.branch_id == branch_id, Room.status == "OCCUPIED", Room.is_active == True)  # noqa: E712
        )
        return total_result.scalar_one(), occupied_result.scalar_one()
