import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_event_publisher
from app.db.session import get_db
from app.producers.base import EventPublisher
from app.repositories.review import ReviewRepository
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def get_review_service(
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> ReviewService:
    return ReviewService(review_repo=ReviewRepository(db), publisher=publisher)


ServiceDep = Annotated[ReviewService, Depends(get_review_service)]


@router.get("", response_model=list[ReviewResponse])
async def list_reviews(svc: ServiceDep, skip: int = 0, limit: int = 100):
    return await svc.list_reviews(skip, limit)


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(payload: ReviewCreate, svc: ServiceDep):
    return await svc.create_review(payload)


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_review(review_id)
