import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.hotel import Branch


class FoodCategory(Base):
    __tablename__ = "food_categories"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="food_categories")
    menu_items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")


class MenuItem(Base):
    __tablename__ = "menu_items"

    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("food_categories.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["FoodCategory"] = relationship("FoodCategory", back_populates="menu_items")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="menu_item")


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    table_number: Mapped[str] = mapped_column(String(20), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    # AVAILABLE | OCCUPIED | RESERVED
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", nullable=False)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="restaurant_tables")
    orders: Mapped[list["RestaurantOrder"]] = relationship("RestaurantOrder", back_populates="table")


class RestaurantOrder(Base):
    __tablename__ = "restaurant_orders"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    table_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=True)
    # OPEN | CLOSED | CANCELLED
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    branch: Mapped["Branch"] = relationship("Branch", back_populates="restaurant_orders")
    table: Mapped["RestaurantTable | None"] = relationship("RestaurantTable", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["RestaurantOrder"] = relationship("RestaurantOrder", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="order_items")
