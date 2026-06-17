import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FoodCategoryCreate(BaseModel):
    branch_id: uuid.UUID
    name: str
    display_order: int = 0


class FoodCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    display_order: int


class MenuItemCreate(BaseModel):
    category_id: uuid.UUID
    name: str
    description: str | None = None
    price: Decimal
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    is_available: bool | None = None


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str | None
    price: Decimal
    is_available: bool


class RestaurantTableCreate(BaseModel):
    branch_id: uuid.UUID
    table_number: str
    capacity: int = 4


class RestaurantTableStatusUpdate(BaseModel):
    status: str  # AVAILABLE | OCCUPIED | RESERVED


class RestaurantTableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    table_number: str
    capacity: int
    status: str


class OrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    menu_item_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    menu_item: MenuItemResponse | None = None


class OrderCreate(BaseModel):
    branch_id: uuid.UUID
    table_id: uuid.UUID | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    table_id: uuid.UUID | None
    status: str
    opened_at: datetime
    closed_at: datetime | None
    total_amount: Decimal
    items: list[OrderItemResponse] = []
