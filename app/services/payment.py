import uuid
from typing import Sequence

from fastapi import HTTPException, status

from app.events.schemas import BaseEvent, PaymentCompleted, RefundIssued
from app.events.topics import PAYMENT_EVENTS
from app.models.payment import Payment
from app.producers.base import EventPublisher
from app.repositories.payment import PaymentRepository
from app.schemas.payment import PaymentCreate, RefundRequest


class PaymentService:
    def __init__(self, payment_repo: PaymentRepository, publisher: EventPublisher) -> None:
        self.payment_repo = payment_repo
        self.publisher = publisher

    async def list_payments(self, skip: int, limit: int) -> Sequence[Payment]:
        return await self.payment_repo.get_all(skip=skip, limit=limit)

    async def get_payment(self, payment_id: uuid.UUID) -> Payment:
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment

    async def create_payment(self, payload: PaymentCreate) -> Payment:
        payment = await self.payment_repo.create({**payload.model_dump(), "status": "COMPLETED"})

        event = BaseEvent(
            event_type="PaymentCompleted",
            aggregate_type="Payment",
            aggregate_id=str(payment.id),
            payload=PaymentCompleted(
                payment_id=payment.id,
                reservation_id=payment.reservation_id,
                order_id=payment.order_id,
                amount=payment.amount,
                method=payment.method,
                status=payment.status,
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, PAYMENT_EVENTS)
        return payment

    async def refund_payment(self, payment_id: uuid.UUID, payload: RefundRequest) -> Payment:
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only completed payments can be refunded",
            )
        payment = await self.payment_repo.update(
            payment, {"status": "REFUNDED", "refund_reason": payload.reason}
        )

        event = BaseEvent(
            event_type="RefundIssued",
            aggregate_type="Payment",
            aggregate_id=str(payment.id),
            payload=RefundIssued(
                payment_id=payment.id,
                amount=payment.amount,
                reason=payment.refund_reason,
                status=payment.status,
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(event, PAYMENT_EVENTS)
        return payment
