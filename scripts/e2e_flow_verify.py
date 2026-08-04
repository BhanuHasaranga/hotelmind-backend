"""Drive the live stack end-to-end for Phase 7 QA and print captured evidence
at every hop: HTTP -> Postgres -> Kafka -> Consumer -> Redis -> WebSocket.

Run inside the backend/consumer network (has hostnames postgres/kafka/redis):

    docker cp scripts/e2e_flow_verify.py hotelmind-backend-1:/app/scripts/e2e_flow_verify.py
    docker exec hotelmind-backend-1 python -m scripts.e2e_flow_verify
"""

from __future__ import annotations

import asyncio
import json
import uuid
from decimal import Decimal

import httpx
import websockets
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from redis.asyncio import Redis

from app.core.config import settings
from app.events.schemas import BaseEvent, OccupancyForecastReady
from app.events.topics import BOOKING_EVENTS, ML_PREDICTIONS

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/dashboard"


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


async def kafka_peek(topic: str, timeout: float = 8.0, match_event_id: str | None = None) -> dict | None:
    """Consume with a throwaway group from the end backwards briefly — used
    to *observe* the last matching message on a topic without disturbing the
    real consumer groups' offsets (own group_id, own commit)."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"qa-observer-{uuid.uuid4().hex[:8]}",
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    try:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            try:
                batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=max(remaining, 0.1))
            except asyncio.TimeoutError:
                continue
            for records in batch.values():
                for record in records:
                    if match_event_id is None or record.value.get("event_id") == match_event_id:
                        return record.value
        return None
    finally:
        await consumer.stop()


async def ws_listen(duration: float = 6.0) -> list[dict]:
    messages: list[dict] = []
    try:
        async with websockets.connect(WS_URL) as ws:
            deadline = asyncio.get_event_loop().time() + duration
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    messages.append(json.loads(raw))
                except asyncio.TimeoutError:
                    break
    except Exception as exc:
        print(f"  [ws error] {exc}")
    return messages


async def flow1_create_reservation(client: httpx.AsyncClient) -> None:
    section("FLOW 1: Create reservation -> Kafka -> BookingConsumer -> Redis -> WebSocket")

    hotels = (await client.get("/api/v1/hotels/")).json()
    branch = hotels[0]["branches"][0]
    branch_id = branch["id"]
    rooms = (await client.get(f"/api/v1/hotels/branches/{branch_id}/rooms")).json()
    room = rooms[0]
    guests = (await client.get("/api/v1/bookings/guests", params={"limit": 1})).json()
    guest = guests[0]

    ws_task = asyncio.create_task(ws_listen(duration=8.0))
    kafka_task = asyncio.create_task(kafka_peek(BOOKING_EVENTS, timeout=8.0))
    await asyncio.sleep(0.3)

    resp = await client.post(
        "/api/v1/bookings/reservations",
        json={
            "room_id": room["id"],
            "guest_id": guest["id"],
            "check_in_date": "2026-09-01",
            "check_out_date": "2026-09-04",
            "adults": 2,
            "children": 0,
            "total_amount": "300.00",
        },
    )
    print(f"HTTP POST /bookings/reservations -> {resp.status_code}")
    print(f"  response: {resp.text[:300]}")
    reservation = resp.json()
    reservation_id = reservation["id"]

    kafka_event = await kafka_task
    print(f"\nKafka booking.events message observed: {json.dumps(kafka_event, indent=2)[:600] if kafka_event else 'NONE (timeout)'}")

    ws_messages = await ws_task
    print(f"\nWebSocket messages received during window ({len(ws_messages)}):")
    for m in ws_messages[:5]:
        print(f"  {json.dumps(m)[:300]}")

    r = Redis.from_url("redis://redis:6379/0", decode_responses=True)
    booking_count = await r.get(f"dashboard:booking_count:{branch_id}")
    print(f"\nRedis dashboard:booking_count:{branch_id} = {booking_count}")
    await r.close()

    print(f"\nReservation status in DB (via GET): ", end="")
    r2 = await client.get(f"/api/v1/bookings/reservations/{reservation_id}")
    print(r2.json()["status"])

    return reservation_id, branch_id


async def flow2_cancel_reservation(client: httpx.AsyncClient, reservation_id: str, branch_id: str) -> None:
    section("FLOW 2: Cancel reservation -> revenue/occupancy Redis update -> WebSocket")

    ws_task = asyncio.create_task(ws_listen(duration=6.0))
    await asyncio.sleep(0.3)

    resp = await client.patch(
        f"/api/v1/bookings/reservations/{reservation_id}/cancel",
        json={"reason": "QA flow test cancellation"},
    )
    print(f"HTTP PATCH .../cancel -> {resp.status_code}: {resp.text[:300]}")

    ws_messages = await ws_task
    print(f"\nWebSocket messages received ({len(ws_messages)}):")
    for m in ws_messages[:5]:
        print(f"  {json.dumps(m)[:300]}")

    r = Redis.from_url("redis://redis:6379/0", decode_responses=True)
    revenue = await r.get(f"dashboard:revenue:{branch_id}")
    booking_count = await r.get(f"dashboard:booking_count:{branch_id}")
    print(f"\nRedis dashboard:revenue:{branch_id} = {revenue}")
    print(f"Redis dashboard:booking_count:{branch_id} = {booking_count}")
    await r.close()


async def flow3_restaurant_order(client: httpx.AsyncClient) -> None:
    section("FLOW 3: Restaurant order -> Kafka -> RestaurantConsumer -> revenue cache -> dashboard")

    hotels = (await client.get("/api/v1/hotels/")).json()
    branch_id = hotels[0]["branches"][0]["id"]
    tables = (await client.get("/api/v1/restaurant/tables", params={"branch_id": branch_id})).json()
    items = (await client.get("/api/v1/restaurant/menu-items", params={"category_id": None})).json() if False else []
    categories = (await client.get("/api/v1/restaurant/categories", params={"branch_id": branch_id})).json()
    menu_items = (await client.get("/api/v1/restaurant/menu-items", params={"category_id": categories[0]["id"]})).json()

    resp = await client.post("/api/v1/restaurant/orders", json={"branch_id": branch_id, "table_id": tables[0]["id"]})
    order = resp.json()
    print(f"HTTP POST /restaurant/orders -> {resp.status_code}: {order.get('id')}")

    resp2 = await client.post(
        f"/api/v1/restaurant/orders/{order['id']}/items",
        json={"menu_item_id": menu_items[0]["id"], "quantity": 2},
    )
    print(f"HTTP POST .../items -> {resp2.status_code}")

    ws_task = asyncio.create_task(ws_listen(duration=6.0))
    kafka_task = asyncio.create_task(kafka_peek("restaurant.events", timeout=6.0))
    await asyncio.sleep(0.3)

    resp3 = await client.patch(f"/api/v1/restaurant/orders/{order['id']}/close")
    closed_order = resp3.json()
    print(f"HTTP PATCH .../close -> {resp3.status_code}: total_amount={closed_order.get('total_amount')}")

    kafka_event = await kafka_task
    print(f"\nKafka restaurant.events message: {json.dumps(kafka_event, indent=2)[:500] if kafka_event else 'NONE'}")

    ws_messages = await ws_task
    print(f"\nWebSocket messages ({len(ws_messages)}):")
    for m in ws_messages[:5]:
        print(f"  {json.dumps(m)[:300]}")

    r = Redis.from_url("redis://redis:6379/0", decode_responses=True)
    sales = await r.get(f"dashboard:restaurant_sales:{branch_id}")
    print(f"\nRedis dashboard:restaurant_sales:{branch_id} = {sales}")
    await r.close()


async def flow4_review(client: httpx.AsyncClient) -> None:
    section("FLOW 4: Submit review -> Kafka -> ReviewConsumer -> sentiment -> dashboard")

    guests = (await client.get("/api/v1/bookings/guests", params={"limit": 1})).json()
    guest = guests[0]

    kafka_task = asyncio.create_task(kafka_peek("review.events", timeout=8.0))
    await asyncio.sleep(0.3)

    resp = await client.post(
        "/api/v1/reviews",
        json={"guest_id": guest["id"], "rating": 5, "comment": "Absolutely fantastic stay, wonderful service!"},
    )
    print(f"HTTP POST /reviews -> {resp.status_code}: {resp.text[:400]}")
    review = resp.json()

    await asyncio.sleep(2.0)
    r2 = await client.get(f"/api/v1/reviews/{review['id']}")
    print(f"\nGET /reviews/{{id}} after processing -> sentiment={r2.json().get('sentiment')} score={r2.json().get('sentiment_score')}")

    kafka_event = await kafka_task
    print(f"\nKafka review.events message: {json.dumps(kafka_event, indent=2)[:500] if kafka_event else 'NONE'}")


async def flow5_ml_event() -> None:
    section("FLOW 5: Publish OccupancyForecastReady directly -> MLConsumer -> Redis -> dashboard -> WebSocket")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        hotels = (await client.get("/api/v1/hotels/")).json()
        branch_id = hotels[0]["branches"][0]["id"]

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda e: e.model_dump_json().encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    await producer.start()

    event = BaseEvent(
        event_type="OccupancyForecastReady",
        aggregate_type="Branch",
        aggregate_id=branch_id,
        payload=OccupancyForecastReady(
            branch_id=branch_id, forecast_date="2026-09-10", predicted_occupancy_pct=78.5
        ).model_dump(mode="json"),
    )

    ws_task = asyncio.create_task(ws_listen(duration=6.0))
    await asyncio.sleep(0.3)

    try:
        await producer.send_and_wait(ML_PREDICTIONS, value=event, key=event.aggregate_id)
        print(f"Published OccupancyForecastReady event_id={event.event_id} to {ML_PREDICTIONS}")
    finally:
        await producer.stop()

    ws_messages = await ws_task
    print(f"\nWebSocket messages ({len(ws_messages)}):")
    for m in ws_messages[:5]:
        print(f"  {json.dumps(m)[:300]}")

    r = Redis.from_url("redis://redis:6379/0", decode_responses=True)
    key = f"dashboard:forecast:OccupancyForecast:{branch_id}"
    val = await r.get(key)
    print(f"\nRedis {key} = {val}")
    await r.close()


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        reservation_id, branch_id = await flow1_create_reservation(client)
        await flow2_cancel_reservation(client, reservation_id, branch_id)
        await flow3_restaurant_order(client)
        await flow4_review(client)
    await flow5_ml_event()

    section("DONE")


if __name__ == "__main__":
    asyncio.run(main())
