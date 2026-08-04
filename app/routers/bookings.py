import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_event_publisher
from app.db.session import get_db
from app.producers.base import EventPublisher
from app.repositories.booking import GuestRepository, ReservationRepository
from app.repositories.hotel import RoomRepository
from app.schemas.booking import (
    CancellationRequest,
    GuestCreate,
    GuestResponse,
    GuestUpdate,
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)
from app.services.booking import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def get_booking_service(
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> BookingService:
    return BookingService(
        reservation_repo=ReservationRepository(db),
        guest_repo=GuestRepository(db),
        room_repo=RoomRepository(db),
        publisher=publisher,
    )


ServiceDep = Annotated[BookingService, Depends(get_booking_service)]


# ── Guests ────────────────────────────────────────────────────────────────────

@router.get("/guests", response_model=list[GuestResponse])
async def list_guests(svc: ServiceDep, skip: int = 0, limit: int = 100):
    return await svc.list_guests(skip, limit)


@router.post("/guests", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
async def create_guest(payload: GuestCreate, svc: ServiceDep):
    return await svc.create_guest(payload)


@router.get("/guests/{guest_id}", response_model=GuestResponse)
async def get_guest(guest_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_guest(guest_id)


@router.put("/guests/{guest_id}", response_model=GuestResponse)
async def update_guest(guest_id: uuid.UUID, payload: GuestUpdate, svc: ServiceDep):
    return await svc.update_guest(guest_id, payload)


# ── Reservations ──────────────────────────────────────────────────────────────

@router.get("/reservations", response_model=list[ReservationResponse])
async def list_reservations(
    svc: ServiceDep,
    branch_id: uuid.UUID | None = None,
    res_status: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    return await svc.list_reservations(branch_id, res_status, skip, limit)


@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(payload: ReservationCreate, svc: ServiceDep):
    return await svc.create_reservation(payload)


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(reservation_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_reservation(reservation_id)


@router.put("/reservations/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(reservation_id: uuid.UUID, payload: ReservationUpdate, svc: ServiceDep):
    return await svc.update_reservation(reservation_id, payload)


@router.patch("/reservations/{reservation_id}/confirm", response_model=ReservationResponse)
async def confirm_reservation(reservation_id: uuid.UUID, svc: ServiceDep):
    return await svc.confirm(reservation_id)


@router.patch("/reservations/{reservation_id}/check-in", response_model=ReservationResponse)
async def check_in(reservation_id: uuid.UUID, svc: ServiceDep):
    return await svc.check_in(reservation_id)


@router.patch("/reservations/{reservation_id}/check-out", response_model=ReservationResponse)
async def check_out(reservation_id: uuid.UUID, svc: ServiceDep):
    return await svc.check_out(reservation_id)


@router.patch("/reservations/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(reservation_id: uuid.UUID, payload: CancellationRequest, svc: ServiceDep):
    return await svc.cancel(reservation_id, payload)
