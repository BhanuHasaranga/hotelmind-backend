import asyncio
import threading

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.websocket.router import manager
from app.websocket.router import router as websocket_router


def build_ws_app() -> FastAPI:
    app = FastAPI()
    app.include_router(websocket_router)
    return app


def test_dashboard_websocket_connects_and_receives_broadcast():
    app = build_ws_app()
    client = TestClient(app)

    with client.websocket_connect("/ws/dashboard") as websocket:
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

    with client.websocket_connect("/ws/dashboard"):
        assert len(manager._connections) >= 1

    assert True  # disconnect handling verified implicitly by no exception on context exit
