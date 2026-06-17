import uuid
from typing import Sequence

from fastapi import HTTPException, status

from app.models.hotel import Hotel, Branch, Floor, RoomType, Room
from app.repositories.hotel import (
    BranchRepository,
    FloorRepository,
    HotelRepository,
    RoomRepository,
    RoomTypeRepository,
)
from app.schemas.hotel import (
    BranchCreate,
    BranchUpdate,
    FloorCreate,
    HotelCreate,
    HotelUpdate,
    RoomCreate,
    RoomStatusUpdate,
    RoomTypeCreate,
    RoomTypeUpdate,
)


class HotelService:
    def __init__(
        self,
        hotel_repo: HotelRepository,
        branch_repo: BranchRepository,
        floor_repo: FloorRepository,
        room_type_repo: RoomTypeRepository,
        room_repo: RoomRepository,
    ) -> None:
        self.hotel_repo = hotel_repo
        self.branch_repo = branch_repo
        self.floor_repo = floor_repo
        self.room_type_repo = room_type_repo
        self.room_repo = room_repo

    # ── Hotels ────────────────────────────────────────────────────────────────

    async def list_hotels(self, skip: int, limit: int) -> Sequence[Hotel]:
        return await self.hotel_repo.get_all_active(skip=skip, limit=limit)

    async def get_hotel(self, hotel_id: uuid.UUID) -> Hotel:
        hotel = await self.hotel_repo.get_with_branches(hotel_id)
        if not hotel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
        return hotel

    async def create_hotel(self, payload: HotelCreate) -> Hotel:
        return await self.hotel_repo.create(payload.model_dump())

    async def update_hotel(self, hotel_id: uuid.UUID, payload: HotelUpdate) -> Hotel:
        hotel = await self.hotel_repo.get(hotel_id)
        if not hotel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
        return await self.hotel_repo.update(hotel, payload.model_dump(exclude_none=True))

    async def deactivate_hotel(self, hotel_id: uuid.UUID) -> None:
        hotel = await self.hotel_repo.get(hotel_id)
        if not hotel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
        await self.hotel_repo.update(hotel, {"is_active": False})

    # ── Branches ──────────────────────────────────────────────────────────────

    async def list_branches(self, hotel_id: uuid.UUID) -> Sequence[Branch]:
        return await self.branch_repo.get_by_hotel(hotel_id)

    async def create_branch(self, payload: BranchCreate) -> Branch:
        return await self.branch_repo.create(payload.model_dump())

    async def update_branch(self, branch_id: uuid.UUID, payload: BranchUpdate) -> Branch:
        branch = await self.branch_repo.get(branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        return await self.branch_repo.update(branch, payload.model_dump(exclude_none=True))

    # ── Room Types ────────────────────────────────────────────────────────────

    async def list_room_types(self, branch_id: uuid.UUID) -> Sequence[RoomType]:
        return await self.room_type_repo.get_by_branch(branch_id)

    async def create_room_type(self, payload: RoomTypeCreate) -> RoomType:
        return await self.room_type_repo.create(payload.model_dump())

    async def update_room_type(self, room_type_id: uuid.UUID, payload: RoomTypeUpdate) -> RoomType:
        rt = await self.room_type_repo.get(room_type_id)
        if not rt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
        return await self.room_type_repo.update(rt, payload.model_dump(exclude_none=True))

    # ── Floors ────────────────────────────────────────────────────────────────

    async def create_floor(self, payload: FloorCreate) -> Floor:
        return await self.floor_repo.create(payload.model_dump())

    # ── Rooms ─────────────────────────────────────────────────────────────────

    async def list_rooms(self, branch_id: uuid.UUID, status: str | None) -> Sequence[Room]:
        return await self.room_repo.get_by_branch(branch_id, status=status)

    async def create_room(self, payload: RoomCreate) -> Room:
        return await self.room_repo.create(payload.model_dump())

    async def update_room_status(self, room_id: uuid.UUID, payload: RoomStatusUpdate) -> Room:
        room = await self.room_repo.get(room_id)
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        allowed = {"AVAILABLE", "OCCUPIED", "MAINTENANCE", "CLEANING"}
        if payload.status not in allowed:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status must be one of {allowed}")
        return await self.room_repo.update(room, {"status": payload.status})
