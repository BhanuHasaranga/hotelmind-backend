from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.websocket.manager import ConnectionManager

router = APIRouter(tags=["WebSocket"])

manager = ConnectionManager()


@router.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket, token: str | None = None) -> None:
    # Browsers cannot set Authorization headers on the WS handshake, so the
    # token is passed as a query param: ws://.../ws/dashboard?token=<jwt>.
    # Close with policy-violation (1008) on missing/invalid/expired token -
    # this check happens before accept() and does not touch the pubsub-bridge
    # broadcast flow at all.
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        decode_access_token(token)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
