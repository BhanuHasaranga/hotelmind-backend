import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AmenityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    icon: str | None


class AmenityCreate(BaseModel):
    name: str
    icon: str | None = None


# ── Room Type ─────────────────────────────────────────────────────────────────

class RoomTypeCreate(BaseModel):
    branch_id: uuid.UUID
    name: str
    base_price: Decimal
    max_occupancy: int = 2
    description: str | None = None


class RoomTypeUpdate(BaseModel):
    name: str | None = None
    base_price: Decimal | None = None
    max_occupancy: int | None = None
    description: str | None = None


class RoomTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    base_price: Decimal
    max_occupancy: int
    description: str | None
    amenities: list[AmenityResponse] = []


# ── Room ──────────────────────────────────────────────────────────────────────

class RoomCreate(BaseModel):
    floor_id: uuid.UUID
    room_type_id: uuid.UUID
    room_number: str


class RoomStatusUpdate(BaseModel):
    status: str  # AVAILABLE | OCCUPIED | MAINTENANCE | CLEANING


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    floor_id: uuid.UUID
    room_type_id: uuid.UUID
    room_number: str
    status: str
    is_active: bool
    room_type: RoomTypeResponse | None = None


# ── Floor ─────────────────────────────────────────────────────────────────────

class FloorCreate(BaseModel):
    branch_id: uuid.UUID
    floor_number: int
    name: str | None = None


class FloorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    floor_number: int
    name: str | None
    rooms: list[RoomResponse] = []


# ── Branch ────────────────────────────────────────────────────────────────────

class BranchCreate(BaseModel):
    hotel_id: uuid.UUID
    name: str
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    is_main_branch: bool = False


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    is_main_branch: bool | None = None


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    hotel_id: uuid.UUID
    name: str
    address: str | None
    city: str | None
    phone: str | None
    is_main_branch: bool


# ── Hotel ─────────────────────────────────────────────────────────────────────

class HotelCreate(BaseModel):
    name: str
    star_rating: int = 3
    address: str
    city: str
    country: str
    phone: str | None = None
    email: str | None = None


class HotelUpdate(BaseModel):
    name: str | None = None
    star_rating: int | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None


class HotelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    star_rating: int
    address: str
    city: str
    country: str
    phone: str | None
    email: str | None
    is_active: bool
    branches: list[BranchResponse] = []
