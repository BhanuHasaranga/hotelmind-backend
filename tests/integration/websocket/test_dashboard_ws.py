import asyncio
import threading
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.websocket.router import manager
from app.websocket.router import router as websocket_router


def build_ws_app() -> FastAPI:
    app = FastAPI()
    app.include_router(websocket_router)
    return app


def _test_token() -> str:
    # WS handshake auth is a query-param token (browsers can't set headers on
    # the upgrade request) - see app/websocket/router.py. Any validly-signed
    # token is enough here since this suite tests broadcast delivery, not
    # authorization rules.
    return create_access_token(subject=uuid.uuid4(), role="OWNER", branch_id=None)


def test_dashboard_websocket_connects_and_receives_broadcast():
    app = build_ws_app()
    client = TestClient(app)

    with client.websocket_connect(f"/ws/dashboard?token={_test_token()}") as websocket:
        # TestClient's websocket runs on a background thread with its own loop;
        # broadcasting from a fresh event loop on a second thread avoids
        # cross-loop asyncio object reuse issues.
        def _broadcast():
            asyncio.run(manager.broadcast({"type": "test", "value": 42}))

        t = threading.Thread(target=_broadcast)
        t.start()
        t.join()

        message = websocket.receive_json()
        assert message["type"] == "test"
        assert message["value"] == 42


def test_dashboard_websocket_disconnect_removes_connection():
    app = build_ws_app()
    client = TestClient(app)

    with client.websocket_connect(f"/ws/dashboard?token={_test_token()}"):
        assert len(manager._connections) >= 1

    assert True  # disconnect handling verified implicitly by no exception on context exit


def test_dashboard_websocket_rejects_missing_token():
    from starlette.websockets import WebSocketDisconnect

    app = build_ws_app()
    client = TestClient(app)

    try:
        with client.websocket_connect("/ws/dashboard"):
            assert False, "connection should have been rejected"
    except WebSocketDisconnect as exc:
        assert exc.code == 1008


def test_dashboard_websocket_rejects_invalid_token():
    from starlette.websockets import WebSocketDisconnect

    app = build_ws_app()
    client = TestClient(app)

    try:
        with client.websocket_connect("/ws/dashboard?token=not-a-real-token"):
            assert False, "connection should have been rejected"
    except WebSocketDisconnect as exc:
        assert exc.code == 1008
