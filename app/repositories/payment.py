import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Reservation
from app.models.hotel import Floor, Room
from app.models.payment import Payment
from app.models.restaurant import RestaurantOrder
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Payment, db)

    async def resolve_branch_id(
        self, reservation_id: uuid.UUID | None, order_id: uuid.UUID | None
    ) -> uuid.UUID | None:
        """Resolves the owning branch via reservation (room -> floor -> branch) or order (branch_id direct)."""
        if order_id is not None:
            result = await self.db.execute(
                select(RestaurantOrder.branch_id).where(RestaurantOrder.id == order_id)
            )
            return result.scalar_one_or_none()
        if reservation_id is not None:
            result = await self.db.execute(
                select(Floor.branch_id)
                .join(Room, Room.floor_id == Floor.id)
                .join(Reservation, Reservation.room_id == Room.id)
                .where(Reservation.id == reservation_id)
            )
            return result.scalar_one_or_none()
        return None
