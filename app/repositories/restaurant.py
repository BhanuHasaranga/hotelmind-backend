import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.restaurant import FoodCategory, MenuItem, OrderItem, RestaurantOrder, RestaurantTable
from app.repositories.base import BaseRepository


class FoodCategoryRepository(BaseRepository[FoodCategory]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(FoodCategory, db)

    async def get_by_branch(self, branch_id: uuid.UUID) -> Sequence[FoodCategory]:
        result = await self.db.execute(
            select(FoodCategory)
            .where(FoodCategory.branch_id == branch_id)
            .order_by(FoodCategory.display_order)
        )
        return result.scalars().all()


class MenuItemRepository(BaseRepository[MenuItem]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(MenuItem, db)

    async def get_by_category(self, category_id: uuid.UUID) -> Sequence[MenuItem]:
        result = await self.db.execute(
            select(MenuItem).where(MenuItem.category_id == category_id)
        )
        return result.scalars().all()


class RestaurantTableRepository(BaseRepository[RestaurantTable]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RestaurantTable, db)

    async def get_by_branch(self, branch_id: uuid.UUID) -> Sequence[RestaurantTable]:
        result = await self.db.execute(
            select(RestaurantTable).where(RestaurantTable.branch_id == branch_id)
        )
        return result.scalars().all()


class OrderRepository(BaseRepository[RestaurantOrder]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RestaurantOrder, db)

    async def get_with_items(self, order_id: uuid.UUID) -> RestaurantOrder | None:
        result = await self.db.execute(
            select(RestaurantOrder)
            .options(
                selectinload(RestaurantOrder.items).selectinload(OrderItem.menu_item)
            )
            .where(RestaurantOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def filter(
        self,
        branch_id: uuid.UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[RestaurantOrder]:
        query = select(RestaurantOrder).offset(skip).limit(limit)
        if branch_id:
            query = query.where(RestaurantOrder.branch_id == branch_id)
        if status:
            query = query.where(RestaurantOrder.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()


class OrderItemRepository(BaseRepository[OrderItem]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(OrderItem, db)
