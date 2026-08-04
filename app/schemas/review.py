import uuid

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    reservation_id: uuid.UUID | None = None
    guest_id: uuid.UUID | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID | None
    guest_id: uuid.UUID | None
    rating: int
    comment: str | None
    sentiment: str | None
    sentiment_score: float | None
