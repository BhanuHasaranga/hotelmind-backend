import uuid
from datetime import datetime, timezone
from typing import Sequence

from fastapi import HTTPException, status

from app.events.schemas import (
    BaseEvent,
    ReservationCancelled,
    ReservationCheckedIn,
    ReservationCheckedOut,
    ReservationConfirmed,
    ReservationCreated,
    ReservationUpdated,
)
from app.events.topics import BOOKING_EVENTS
from app.models.booking import Guest, Reservation
from app.models.hotel import Room
from app.producers.base import EventPublisher
from app.repositories.booking import GuestRepository, ReservationRepository
from app.repositories.hotel import RoomRepository
from app.schemas.booking import (
    CancellationRequest,
    GuestCreate,
    GuestUpdate,
    ReservationCreate,
    ReservationUpdate,
)

# Valid status transitions: current_status → {allowed next statuses}
_TRANSITIONS: dict[str, set[str]] = {
    "PENDING":     {"CONFIRMED", "CANCELLED"},
    "CONFIRMED":   {"CHECKED_IN", "CANCELLED", "NO_SHOW"},
    "CHECKED_IN":  {"CHECKED_OUT"},
    "CHECKED_OUT": set(),
    "CANCELLED":   set(),
    "NO_SHOW":     set(),
}


class BookingService:
    def __init__(
        self,
        reservation_repo: ReservationRepository,
        guest_repo: GuestRepository,
        room_repo: RoomRepository,
        publisher: EventPublisher,
    ) -> None:
        self.reservation_repo = reservation_repo
        self.guest_repo = guest_repo
        self.room_repo = room_repo
        self.publisher = publisher

    # ── Guests ────────────────────────────────────────────────────────────────

    async def list_guests(self, skip: int, limit: int) -> Sequence[Guest]:
        return await self.guest_repo.get_all(skip=skip, limit=limit)

    async def get_guest(self, guest_id: uuid.UUID) -> Guest:
        guest = await self.guest_repo.get(guest_id)
        if not guest:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
        return guest

    async def create_guest(self, payload: GuestCreate) -> Guest:
        existing = await self.guest_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guest with this email already exists")
        return await self.guest_repo.create(payload.model_dump())

    async def update_guest(self, guest_id: uuid.UUID, payload: GuestUpdate) -> Guest:
        guest = await self.guest_repo.get(guest_id)
        if not guest:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
        return await self.guest_repo.update(guest, payload.model_dump(exclude_none=True))

    # ── Reservations ──────────────────────────────────────────────────────────

    async def list_reservations(
        self,
        branch_id: uuid.UUID | None,
        res_status: str | None,
        skip: int,
        limit: int,
    ) -> Sequence[Reservation]:
        return await self.reservation_repo.filter(
            branch_id=branch_id, status=res_status, skip=skip, limit=limit
        )

    async def get_reservation(self, reservation_id: uuid.UUID) -> Reservation:
        res = await self.reservation_repo.get_with_guest(reservation_id)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        return res

    async def create_reservation(self, payload: ReservationCreate) -> Reservation:
        conflict = await self.reservation_repo.has_conflict(
            payload.room_id, payload.check_in_date, payload.check_out_date
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room is already booked for the requested dates",
            )
        new_res = await self.reservation_repo.create(payload.model_dump())
        res = await self.reservation_repo.get_with_guest(new_res.id)

        event = BaseEvent(
            event_type="ReservationCreated",
            aggregate_type="Reservation",
            aggregate_id=str(res.id),
            payload=ReservationCreated(
                reservation_id=res.id,
                room_id=res.room_id,
                guest_id=res.guest_id,
                check_in_date=res.check_in_date,
                check_out_date=res.check_out_date,
                status=res.status,
                total_amount=res.total_amount,
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, BOOKING_EVENTS)
        return res  # type: ignore[return-value]

    async def update_reservation(self, reservation_id: uuid.UUID, payload: ReservationUpdate) -> Reservation:
        res = await self.reservation_repo.get(reservation_id)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        data = payload.model_dump(exclude_none=True)
        if "check_in_date" in data or "check_out_date" in data:
            new_in = data.get("check_in_date", res.check_in_date)
            new_out = data.get("check_out_date", res.check_out_date)
            conflict = await self.reservation_repo.has_conflict(
                res.room_id, new_in, new_out, exclude_id=reservation_id
            )
            if conflict:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Date conflict with existing reservation")
        await self.reservation_repo.update(res, data)
        updated = await self.reservation_repo.get_with_guest(reservation_id)

        event = BaseEvent(
            event_type="ReservationUpdated",
            aggregate_type="Reservation",
            aggregate_id=str(reservation_id),
            payload=ReservationUpdated(
                reservation_id=reservation_id,
                status=updated.status,
                changes={k: v for k, v in data.items()},
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, BOOKING_EVENTS)
        return updated  # type: ignore[return-value]

    async def _transition(self, reservation_id: uuid.UUID, target_status: str) -> Reservation:
        res = await self.reservation_repo.get(reservation_id)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        allowed = _TRANSITIONS.get(res.status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot transition from {res.status} to {target_status}",
            )
        return res

    async def confirm(self, reservation_id: uuid.UUID) -> Reservation:
        res = await self._transition(reservation_id, "CONFIRMED")
        await self.reservation_repo.update(res, {"status": "CONFIRMED"})
        updated = await self.reservation_repo.get_with_guest(reservation_id)

        event = BaseEvent(
            event_type="ReservationConfirmed",
            aggregate_type="Reservation",
            aggregate_id=str(reservation_id),
            payload=ReservationConfirmed(reservation_id=reservation_id, status="CONFIRMED").model_dump(mode="json"),
        )
        await self.publisher.publish(event, BOOKING_EVENTS)
        return updated  # type: ignore[return-value]

    async def check_in(self, reservation_id: uuid.UUID) -> Reservation:
        res = await self._transition(reservation_id, "CHECKED_IN")
        await self.reservation_repo.update(res, {"status": "CHECKED_IN"})
        room = await self.room_repo.get(res.room_id)
        if room:
            await self.room_repo.update(room, {"status": "OCCUPIED"})
        updated = await self.reservation_repo.get_with_guest(reservation_id)

        event = BaseEvent(
            event_type="ReservationCheckedIn",
            aggregate_type="Reservation",
            aggregate_id=str(reservation_id),
            payload=ReservationCheckedIn(
                reservation_id=reservation_id, room_id=res.room_id, status="CHECKED_IN"
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, BOOKING_EVENTS)
        return updated  # type: ignore[return-value]

    async def check_out(self, reservation_id: uuid.UUID) -> Reservation:
        res = await self._transition(reservation_id, "CHECKED_OUT")
        await self.reservation_repo.update(res, {"status": "CHECKED_OUT"})
        room = await self.room_repo.get(res.room_id)
        if room:
            await self.room_repo.update(room, {"status": "AVAILABLE"})
        updated = await self.reservation_repo.get_with_guest(reservation_id)

        event = BaseEvent(
            event_type="ReservationCheckedOut",
            aggregate_type="Reservation",
            aggregate_id=str(reservation_id),
            payload=ReservationCheckedOut(
                reservation_id=reservation_id, room_id=res.room_id, status="CHECKED_OUT"
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, BOOKING_EVENTS)
        return updated  # type: ignore[return-value]

    async def cancel(self, reservation_id: uuid.UUID, payload: CancellationRequest) -> Reservation:
        res = await self._transition(reservation_id, "CANCELLED")
        await self.reservation_repo.update(res, {
            "status": "CANCELLED",
            "cancelled_at": datetime.now(timezone.utc),
            "cancellation_reason": payload.reason,
        })
        updated = await self.reservation_repo.get_with_guest(reservation_id)

        event = BaseEvent(
            event_type="ReservationCancelled",
            aggregate_type="Reservation",
            aggregate_id=str(reservation_id),
            payload=ReservationCancelled(
                reservation_id=reservation_id, status="CANCELLED", cancellation_reason=payload.reason
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, BOOKING_EVENTS)
        return updated  # type: ignore[return-value]
