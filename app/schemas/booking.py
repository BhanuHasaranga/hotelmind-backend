import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class GuestCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    id_type: str | None = None
    id_number: str | None = None
    nationality: str | None = None


class GuestUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    id_type: str | None = None
    id_number: str | None = None
    nationality: str | None = None


class GuestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    nationality: str | None


# ── Reservation ───────────────────────────────────────────────────────────────

class ReservationCreate(BaseModel):
    room_id: uuid.UUID
    guest_id: uuid.UUID
    check_in_date: date
    check_out_date: date
    adults: int = 1
    children: int = 0
    total_amount: Decimal
    special_requests: str | None = None

    @field_validator("check_out_date")
    @classmethod
    def checkout_after_checkin(cls, v: date, info) -> date:
        check_in = info.data.get("check_in_date")
        if check_in and v <= check_in:
            raise ValueError("check_out_date must be after check_in_date")
        return v


class ReservationUpdate(BaseModel):
    check_in_date: date | None = None
    check_out_date: date | None = None
    adults: int | None = None
    children: int | None = None
    special_requests: str | None = None
    paid_amount: Decimal | None = None


class CancellationRequest(BaseModel):
    reason: str | None = None


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    room_id: uuid.UUID
    guest_id: uuid.UUID
    check_in_date: date
    check_out_date: date
    status: str
    adults: int
    children: int
    total_amount: Decimal
    paid_amount: Decimal
    special_requests: str | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    guest: GuestResponse | None = None
