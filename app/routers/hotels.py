import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.hotel import (
    BranchRepository,
    FloorRepository,
    HotelRepository,
    RoomRepository,
    RoomTypeRepository,
)
from app.schemas.hotel import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    FloorCreate,
    FloorResponse,
    HotelCreate,
    HotelResponse,
    HotelUpdate,
    RoomCreate,
    RoomResponse,
    RoomStatusUpdate,
    RoomTypeCreate,
    RoomTypeResponse,
    RoomTypeUpdate,
)
from app.services.hotel import HotelService

router = APIRouter(prefix="/hotels", tags=["Hotels"])


def get_hotel_service(db: AsyncSession = Depends(get_db)) -> HotelService:
    return HotelService(
        hotel_repo=HotelRepository(db),
        branch_repo=BranchRepository(db),
        floor_repo=FloorRepository(db),
        room_type_repo=RoomTypeRepository(db),
        room_repo=RoomRepository(db),
    )


ServiceDep = Annotated[HotelService, Depends(get_hotel_service)]


@router.get("/", response_model=list[HotelResponse])
async def list_hotels(svc: ServiceDep, skip: int = 0, limit: int = 100):
    return await svc.list_hotels(skip, limit)


@router.post("/", response_model=HotelResponse, status_code=status.HTTP_201_CREATED)
async def create_hotel(payload: HotelCreate, svc: ServiceDep):
    return await svc.create_hotel(payload)


@router.get("/{hotel_id}", response_model=HotelResponse)
async def get_hotel(hotel_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_hotel(hotel_id)


@router.put("/{hotel_id}", response_model=HotelResponse)
async def update_hotel(hotel_id: uuid.UUID, payload: HotelUpdate, svc: ServiceDep):
    return await svc.update_hotel(hotel_id, payload)


@router.delete("/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_hotel(hotel_id: uuid.UUID, svc: ServiceDep):
    await svc.deactivate_hotel(hotel_id)


# ── Branches ──────────────────────────────────────────────────────────────────

@router.get("/{hotel_id}/branches", response_model=list[BranchResponse])
async def list_branches(hotel_id: uuid.UUID, svc: ServiceDep):
    return await svc.list_branches(hotel_id)


@router.post("/{hotel_id}/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(hotel_id: uuid.UUID, payload: BranchCreate, svc: ServiceDep):
    payload.hotel_id = hotel_id
    return await svc.create_branch(payload)


@router.put("/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(branch_id: uuid.UUID, payload: BranchUpdate, svc: ServiceDep):
    return await svc.update_branch(branch_id, payload)


# ── Room Types ────────────────────────────────────────────────────────────────

@router.get("/branches/{branch_id}/room-types", response_model=list[RoomTypeResponse])
async def list_room_types(branch_id: uuid.UUID, svc: ServiceDep):
    return await svc.list_room_types(branch_id)


@router.post("/room-types", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(payload: RoomTypeCreate, svc: ServiceDep):
    return await svc.create_room_type(payload)


@router.put("/room-types/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(room_type_id: uuid.UUID, payload: RoomTypeUpdate, svc: ServiceDep):
    return await svc.update_room_type(room_type_id, payload)


# ── Floors ────────────────────────────────────────────────────────────────────

@router.post("/floors", response_model=FloorResponse, status_code=status.HTTP_201_CREATED)
async def create_floor(payload: FloorCreate, svc: ServiceDep):
    return await svc.create_floor(payload)


# ── Rooms ─────────────────────────────────────────────────────────────────────

@router.get("/branches/{branch_id}/rooms", response_model=list[RoomResponse])
async def list_rooms(
    branch_id: uuid.UUID,
    svc: ServiceDep,
    room_status: Annotated[str | None, Query(alias="status")] = None,
):
    return await svc.list_rooms(branch_id, status=room_status)


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, svc: ServiceDep):
    return await svc.create_room(payload)


@router.patch("/rooms/{room_id}/status", response_model=RoomResponse)
async def update_room_status(room_id: uuid.UUID, payload: RoomStatusUpdate, svc: ServiceDep):
    return await svc.update_room_status(room_id, payload)
