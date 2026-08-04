import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_event_publisher
from app.db.session import get_db
from app.producers.base import EventPublisher
from app.repositories.payment import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentResponse, RefundRequest
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


def get_payment_service(
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> PaymentService:
    return PaymentService(payment_repo=PaymentRepository(db), publisher=publisher)


ServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


@router.get("", response_model=list[PaymentResponse])
async def list_payments(svc: ServiceDep, skip: int = 0, limit: int = 100):
    return await svc.list_payments(skip, limit)


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(payload: PaymentCreate, svc: ServiceDep):
    return await svc.create_payment(payload)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_payment(payment_id)


@router.patch("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(payment_id: uuid.UUID, payload: RefundRequest, svc: ServiceDep):
    return await svc.refund_payment(payment_id, payload)
