from abc import ABC, abstractmethod

from app.events.schemas import BaseEvent


class EventPublisher(ABC):
    """Swappable event publishing backend."""

    @abstractmethod
    async def publish(self, event: BaseEvent, topic: str) -> None:
        ...

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...
