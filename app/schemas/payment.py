import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    reservation_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    amount: Decimal
    method: str


class RefundRequest(BaseModel):
    reason: str | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID | None
    order_id: uuid.UUID | None
    amount: Decimal
    method: str
    status: str
    refund_reason: str | None
