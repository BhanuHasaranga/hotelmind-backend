import json
import logging

from fastapi import WebSocket

from app.metrics.prometheus import messages_sent, websocket_connections

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        websocket_connections.set(len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        websocket_connections.set(len(self._connections))

    async def broadcast(self, payload: dict) -> None:
        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(message)
                messages_sent.inc()
            except Exception:
                logger.warning("Failed to send WebSocket message, dropping connection", exc_info=True)
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)
