import uuid
from typing import Sequence

from fastapi import HTTPException, status

from app.events.schemas import BaseEvent, ReviewCreated, SentimentCalculated
from app.events.topics import REVIEW_EVENTS
from app.models.review import Review
from app.producers.base import EventPublisher
from app.repositories.review import ReviewRepository
from app.schemas.review import ReviewCreate
from app.services.sentiment import score_sentiment


class ReviewService:
    def __init__(self, review_repo: ReviewRepository, publisher: EventPublisher) -> None:
        self.review_repo = review_repo
        self.publisher = publisher

    async def list_reviews(self, skip: int, limit: int) -> Sequence[Review]:
        return await self.review_repo.get_all(skip=skip, limit=limit)

    async def get_review(self, review_id: uuid.UUID) -> Review:
        review = await self.review_repo.get(review_id)
        if not review:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
        return review

    async def create_review(self, payload: ReviewCreate) -> Review:
        review = await self.review_repo.create(payload.model_dump())

        created_event = BaseEvent(
            event_type="ReviewCreated",
            aggregate_type="Review",
            aggregate_id=str(review.id),
            payload=ReviewCreated(
                review_id=review.id,
                reservation_id=review.reservation_id,
                guest_id=review.guest_id,
                rating=review.rating,
                comment=review.comment,
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(created_event, REVIEW_EVENTS)

        sentiment, score = score_sentiment(review.comment)
        review = await self.review_repo.update(
            review, {"sentiment": sentiment, "sentiment_score": score}
        )

        sentiment_event = BaseEvent(
            event_type="SentimentCalculated",
            aggregate_type="Review",
            aggregate_id=str(review.id),
            payload=SentimentCalculated(
                review_id=review.id,
                sentiment=sentiment,
                sentiment_score=score,
            ).model_dump(mode="json"),
        )
        await self.publisher.publish(sentiment_event, REVIEW_EVENTS)
        return review
