from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    occupancy_pct: float
    occupied_rooms: int
    total_rooms: int
    revenue_today: Decimal
    revenue_mtd: Decimal
    reservations_today: int
    reservations_pending: int
    restaurant_sales_today: Decimal
    restaurant_orders_open: int


class DailyOccupancy(BaseModel):
    date: str
    occupancy_pct: float
    occupied_rooms: int
    total_rooms: int


class DailyRevenue(BaseModel):
    date: str
    revenue: Decimal
