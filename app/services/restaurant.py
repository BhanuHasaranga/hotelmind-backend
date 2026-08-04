import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from fastapi import HTTPException, status

from app.events.schemas import BaseEvent, OrderCancelled, OrderCompleted, OrderCreated, OrderUpdated
from app.events.topics import RESTAURANT_EVENTS
from app.models.restaurant import FoodCategory, MenuItem, RestaurantOrder, RestaurantTable
from app.producers.base import EventPublisher
from app.repositories.restaurant import (
    FoodCategoryRepository,
    MenuItemRepository,
    OrderItemRepository,
    OrderRepository,
    RestaurantTableRepository,
)
from app.schemas.restaurant import (
    FoodCategoryCreate,
    MenuItemCreate,
    MenuItemUpdate,
    OrderCreate,
    OrderItemCreate,
    RestaurantTableCreate,
    RestaurantTableStatusUpdate,
)


class RestaurantService:
    def __init__(
        self,
        category_repo: FoodCategoryRepository,
        menu_repo: MenuItemRepository,
        table_repo: RestaurantTableRepository,
        order_repo: OrderRepository,
        order_item_repo: OrderItemRepository,
        publisher: EventPublisher,
    ) -> None:
        self.category_repo = category_repo
        self.menu_repo = menu_repo
        self.table_repo = table_repo
        self.order_repo = order_repo
        self.order_item_repo = order_item_repo
        self.publisher = publisher

    # ── Categories ────────────────────────────────────────────────────────────

    async def list_categories(self, branch_id: uuid.UUID) -> Sequence[FoodCategory]:
        return await self.category_repo.get_by_branch(branch_id)

    async def create_category(self, payload: FoodCategoryCreate) -> FoodCategory:
        return await self.category_repo.create(payload.model_dump())

    # ── Menu Items ────────────────────────────────────────────────────────────

    async def list_menu_items(
        self, category_id: uuid.UUID | None, skip: int = 0, limit: int = 200
    ) -> Sequence[MenuItem]:
        if category_id:
            return await self.menu_repo.get_by_category(category_id, skip=skip, limit=limit)
        return await self.menu_repo.get_all(skip=skip, limit=limit)

    async def create_menu_item(self, payload: MenuItemCreate) -> MenuItem:
        return await self.menu_repo.create(payload.model_dump())

    async def update_menu_item(self, item_id: uuid.UUID, payload: MenuItemUpdate) -> MenuItem:
        item = await self.menu_repo.get(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        return await self.menu_repo.update(item, payload.model_dump(exclude_none=True))

    # ── Tables ────────────────────────────────────────────────────────────────

    async def list_tables(self, branch_id: uuid.UUID) -> Sequence[RestaurantTable]:
        return await self.table_repo.get_by_branch(branch_id)

    async def create_table(self, payload: RestaurantTableCreate) -> RestaurantTable:
        return await self.table_repo.create(payload.model_dump())

    async def update_table_status(self, table_id: uuid.UUID, payload: RestaurantTableStatusUpdate) -> RestaurantTable:
        table = await self.table_repo.get(table_id)
        if not table:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
        return await self.table_repo.update(table, {"status": payload.status})

    # ── Orders ────────────────────────────────────────────────────────────────

    async def list_orders(
        self, branch_id: uuid.UUID | None, order_status: str | None, skip: int, limit: int
    ) -> Sequence[RestaurantOrder]:
        return await self.order_repo.filter(branch_id=branch_id, status=order_status, skip=skip, limit=limit)

    async def get_order(self, order_id: uuid.UUID) -> RestaurantOrder:
        order = await self.order_repo.get_with_items(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def open_order(self, payload: OrderCreate) -> RestaurantOrder:
        new_order = await self.order_repo.create({
            "branch_id": payload.branch_id,
            "table_id": payload.table_id,
            "status": "OPEN",
            "opened_at": datetime.now(timezone.utc),
            "total_amount": Decimal("0.00"),
        })
        order = await self.order_repo.get_with_items(new_order.id)

        event = BaseEvent(
            event_type="OrderCreated",
            aggregate_type="RestaurantOrder",
            aggregate_id=str(order.id),
            payload=OrderCreated(
                order_id=order.id, branch_id=order.branch_id, status=order.status, total_amount=order.total_amount
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, RESTAURANT_EVENTS)
        return order  # type: ignore[return-value]

    async def add_item(self, order_id: uuid.UUID, payload: OrderItemCreate) -> RestaurantOrder:
        order = await self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status != "OPEN":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Can only add items to OPEN orders")
        menu_item = await self.menu_repo.get(payload.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        subtotal = menu_item.price * payload.quantity
        await self.order_item_repo.create({
            "order_id": order_id,
            "menu_item_id": payload.menu_item_id,
            "quantity": payload.quantity,
            "unit_price": menu_item.price,
            "subtotal": subtotal,
        })
        new_total = order.total_amount + subtotal
        await self.order_repo.update(order, {"total_amount": new_total})
        updated = await self.order_repo.get_with_items(order_id)

        event = BaseEvent(
            event_type="OrderUpdated",
            aggregate_type="RestaurantOrder",
            aggregate_id=str(order_id),
            payload=OrderUpdated(
                order_id=order_id,
                branch_id=updated.branch_id,
                status=updated.status,
                changes={"item_added": str(payload.menu_item_id)},
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, RESTAURANT_EVENTS)
        return updated  # type: ignore[return-value]

    async def remove_item(self, order_id: uuid.UUID, item_id: uuid.UUID) -> RestaurantOrder:
        order = await self.order_repo.get(order_id)
        if not order or order.status != "OPEN":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Can only modify OPEN orders")
        item = await self.order_item_repo.get(item_id)
        if not item or item.order_id != order_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
        new_total = order.total_amount - item.subtotal
        await self.order_item_repo.delete(item)
        await self.order_repo.update(order, {"total_amount": max(new_total, Decimal("0.00"))})
        updated = await self.order_repo.get_with_items(order_id)

        event = BaseEvent(
            event_type="OrderUpdated",
            aggregate_type="RestaurantOrder",
            aggregate_id=str(order_id),
            payload=OrderUpdated(
                order_id=order_id,
                branch_id=updated.branch_id,
                status=updated.status,
                changes={"item_removed": str(item_id)},
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, RESTAURANT_EVENTS)
        return updated  # type: ignore[return-value]

    async def close_order(self, order_id: uuid.UUID) -> RestaurantOrder:
        order = await self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status != "OPEN":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Order is not open")
        await self.order_repo.update(order, {"status": "CLOSED", "closed_at": datetime.now(timezone.utc)})
        updated = await self.order_repo.get_with_items(order_id)

        event = BaseEvent(
            event_type="OrderCompleted",
            aggregate_type="RestaurantOrder",
            aggregate_id=str(order_id),
            payload=OrderCompleted(
                order_id=order_id, branch_id=updated.branch_id, status=updated.status, total_amount=updated.total_amount
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, RESTAURANT_EVENTS)
        return updated  # type: ignore[return-value]

    async def cancel_order(self, order_id: uuid.UUID) -> RestaurantOrder:
        order = await self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status == "CLOSED":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot cancel a closed order")
        if order.status == "CANCELLED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is already cancelled")
        await self.order_repo.update(order, {"status": "CANCELLED"})
        updated = await self.order_repo.get_with_items(order_id)

        event = BaseEvent(
            event_type="OrderCancelled",
            aggregate_type="RestaurantOrder",
            aggregate_id=str(order_id),
            payload=OrderCancelled(
                order_id=order_id, branch_id=updated.branch_id, status=updated.status
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, RESTAURANT_EVENTS)
        return updated  # type: ignore[return-value]
