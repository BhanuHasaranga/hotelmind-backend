import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import get_current_user, require_roles
from app.core.dependencies import get_event_publisher
from app.db.session import get_db
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
    FoodCategoryResponse,
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
    OrderCreate,
    OrderItemCreate,
    OrderResponse,
    RestaurantTableCreate,
    RestaurantTableResponse,
    RestaurantTableStatusUpdate,
)
from app.services.restaurant import RestaurantService

router = APIRouter(prefix="/restaurant", tags=["Restaurant"], dependencies=[Depends(get_current_user)])

# Mutating restaurant operations restricted to OWNER and RESTAURANT_MANAGER.
manage_roles = Depends(require_roles("OWNER", "RESTAURANT_MANAGER"))


def get_restaurant_service(
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> RestaurantService:
    return RestaurantService(
        category_repo=FoodCategoryRepository(db),
        menu_repo=MenuItemRepository(db),
        table_repo=RestaurantTableRepository(db),
        order_repo=OrderRepository(db),
        order_item_repo=OrderItemRepository(db),
        publisher=publisher,
    )


ServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]


@router.get("/categories", response_model=list[FoodCategoryResponse])
async def list_categories(branch_id: uuid.UUID, svc: ServiceDep):
    return await svc.list_categories(branch_id)


@router.post(
    "/categories", response_model=FoodCategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[manage_roles]
)
async def create_category(payload: FoodCategoryCreate, svc: ServiceDep):
    return await svc.create_category(payload)


@router.get("/menu-items", response_model=list[MenuItemResponse])
async def list_menu_items(
    svc: ServiceDep, category_id: uuid.UUID | None = None, skip: int = 0, limit: int = 200
):
    return await svc.list_menu_items(category_id, skip=skip, limit=limit)


@router.post(
    "/menu-items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED, dependencies=[manage_roles]
)
async def create_menu_item(payload: MenuItemCreate, svc: ServiceDep):
    return await svc.create_menu_item(payload)


@router.put("/menu-items/{item_id}", response_model=MenuItemResponse, dependencies=[manage_roles])
async def update_menu_item(item_id: uuid.UUID, payload: MenuItemUpdate, svc: ServiceDep):
    return await svc.update_menu_item(item_id, payload)


@router.get("/tables", response_model=list[RestaurantTableResponse])
async def list_tables(branch_id: uuid.UUID, svc: ServiceDep):
    return await svc.list_tables(branch_id)


@router.post(
    "/tables", response_model=RestaurantTableResponse, status_code=status.HTTP_201_CREATED, dependencies=[manage_roles]
)
async def create_table(payload: RestaurantTableCreate, svc: ServiceDep):
    return await svc.create_table(payload)


@router.patch("/tables/{table_id}/status", response_model=RestaurantTableResponse, dependencies=[manage_roles])
async def update_table_status(table_id: uuid.UUID, payload: RestaurantTableStatusUpdate, svc: ServiceDep):
    return await svc.update_table_status(table_id, payload)


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(
    svc: ServiceDep,
    branch_id: uuid.UUID | None = None,
    order_status: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    return await svc.list_orders(branch_id, order_status, skip, limit)


@router.post(
    "/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[manage_roles]
)
async def open_order(payload: OrderCreate, svc: ServiceDep):
    return await svc.open_order(payload)


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_order(order_id)


@router.post("/orders/{order_id}/items", response_model=OrderResponse, dependencies=[manage_roles])
async def add_order_item(order_id: uuid.UUID, payload: OrderItemCreate, svc: ServiceDep):
    return await svc.add_item(order_id, payload)


@router.delete("/orders/{order_id}/items/{item_id}", response_model=OrderResponse, dependencies=[manage_roles])
async def remove_order_item(order_id: uuid.UUID, item_id: uuid.UUID, svc: ServiceDep):
    return await svc.remove_item(order_id, item_id)


@router.patch("/orders/{order_id}/close", response_model=OrderResponse, dependencies=[manage_roles])
async def close_order(order_id: uuid.UUID, svc: ServiceDep):
    return await svc.close_order(order_id)


@router.patch("/orders/{order_id}/cancel", response_model=OrderResponse, dependencies=[manage_roles])
async def cancel_order(order_id: uuid.UUID, svc: ServiceDep):
    return await svc.cancel_order(order_id)
