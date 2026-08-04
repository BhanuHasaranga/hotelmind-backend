import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.conftest import requires_docker
from app.main import app
from app.models.guardrail import MlRoomTypeMapping, PricingGuardrail
from app.models.hotel import Branch, RoomType
from app.models.user import User
from app.services.ml_client import MLClient
from app.routers.ml import get_ml_client

pytestmark = requires_docker


class _FakeMLClient(MLClient):
    """Stands in for the real ml-backend HTTP call — no live ML service
    is available in this test environment, so the proxy layer (guardrail
    clamping, Recommendation persistence, role gating) is what's under
    test here, not the ML model itself."""

    def __init__(self, pricing_response: dict | None = None):
        self._pricing_response = pricing_response or {
            "branch_id": 1,
            "room_type_id": 1,
            "date": "2026-08-10",
            "recommended_price": 500.0,
            "expected_revenue": 4500.0,
            "meta": {
                "model_version": "1",
                "trained_at": "2026-08-01T00:00:00Z",
                "latency_ms": 12.5,
                "confidence": 0.9,
            },
        }

    async def predict_pricing(self, **kwargs) -> dict:
        return self._pricing_response


@pytest.fixture(autouse=True)
def _override_ml_client():
    app.dependency_overrides[get_ml_client] = lambda: _FakeMLClient()
    yield
    app.dependency_overrides.pop(get_ml_client, None)


@pytest.mark.asyncio
async def test_pricing_recommend_requires_room_type_mapping(
    client: AsyncClient,
    revenue_manager_token: str,
    seeded_branch: Branch,
    seeded_room_type: RoomType,
):
    response = await client.post(
        "/api/v1/ml/pricing/recommend",
        headers={"Authorization": f"Bearer {revenue_manager_token}"},
        json={
            "branch_id": str(seeded_branch.id),
            "room_type_id": str(seeded_room_type.id),
            "date": "2026-08-10",
            "current_occupancy_pct": 80.0,
            "current_revenue": 4000.0,
            "revenue_7day_avg": 3800.0,
            "total_rooms": 20,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pricing_recommend_forbidden_for_restaurant_manager(
    client: AsyncClient,
    restaurant_manager_token: str,
    seeded_branch: Branch,
    seeded_room_type: RoomType,
):
    response = await client.post(
        "/api/v1/ml/pricing/recommend",
        headers={"Authorization": f"Bearer {restaurant_manager_token}"},
        json={
            "branch_id": str(seeded_branch.id),
            "room_type_id": str(seeded_room_type.id),
            "date": "2026-08-10",
            "current_occupancy_pct": 80.0,
            "current_revenue": 4000.0,
            "revenue_7day_avg": 3800.0,
            "total_rooms": 20,
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pricing_recommend_success_and_guardrail_clamp(
    client: AsyncClient,
    revenue_manager_token: str,
    revenue_manager_user: User,
    seeded_branch: Branch,
    seeded_room_type: RoomType,
    db_session: AsyncSession,
):
    db_session.add(MlRoomTypeMapping(room_type_id=seeded_room_type.id, ml_room_type_id=1))
    db_session.add(
        PricingGuardrail(
            branch_id=seeded_branch.id,
            room_type_id=seeded_room_type.id,
            min_price=100,
            max_price=300,  # below the fake ML response's 500.0 -> should clamp
            max_daily_change_pct=25,
            updated_by_user_id=revenue_manager_user.id,
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/ml/pricing/recommend",
        headers={"Authorization": f"Bearer {revenue_manager_token}"},
        json={
            "branch_id": str(seeded_branch.id),
            "room_type_id": str(seeded_room_type.id),
            "date": "2026-08-10",
            "current_occupancy_pct": 80.0,
            "current_revenue": 4000.0,
            "revenue_7day_avg": 3800.0,
            "total_rooms": 20,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guardrail_clamped"] is True
    assert body["recommended_price"] == 300.0
    assert body["recommendation_id"]


@pytest.mark.asyncio
async def test_recommendation_action_and_apply_to_room_type(
    client: AsyncClient,
    revenue_manager_token: str,
    seeded_branch: Branch,
    seeded_room_type: RoomType,
    db_session: AsyncSession,
):
    db_session.add(MlRoomTypeMapping(room_type_id=seeded_room_type.id, ml_room_type_id=1))
    await db_session.commit()

    recommend_resp = await client.post(
        "/api/v1/ml/pricing/recommend",
        headers={"Authorization": f"Bearer {revenue_manager_token}"},
        json={
            "branch_id": str(seeded_branch.id),
            "room_type_id": str(seeded_room_type.id),
            "date": "2026-08-10",
            "current_occupancy_pct": 80.0,
            "current_revenue": 4000.0,
            "revenue_7day_avg": 3800.0,
            "total_rooms": 20,
        },
    )
    recommendation_id = recommend_resp.json()["recommendation_id"]

    action_resp = await client.post(
        f"/api/v1/recommendations/{recommendation_id}/action",
        headers={"Authorization": f"Bearer {revenue_manager_token}"},
        json={"status": "ACCEPTED"},
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["status"] == "ACCEPTED"

    await db_session.refresh(seeded_room_type)
    assert float(seeded_room_type.base_price) == 500.0


@pytest.mark.asyncio
async def test_list_recommendations_requires_branch_scope(
    client: AsyncClient, revenue_manager_token: str
):
    response = await client.get(
        "/api/v1/recommendations",
        headers={"Authorization": f"Bearer {revenue_manager_token}"},
        params={"branch_id": str(uuid.uuid4())},
    )
    assert response.status_code == 403
