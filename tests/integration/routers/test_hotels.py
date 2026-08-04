import pytest
from httpx import AsyncClient

from tests.integration.conftest import requires_docker
from app.models.hotel import Branch

pytestmark = requires_docker


@pytest.mark.asyncio
async def test_list_hotels_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/hotels/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_hotels_with_valid_token(client: AsyncClient, owner_token: str):
    response = await client.get(
        "/api/v1/hotels/", headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_hotel_forbidden_for_restaurant_manager(
    client: AsyncClient, restaurant_manager_token: str
):
    response = await client.post(
        "/api/v1/hotels/",
        headers={"Authorization": f"Bearer {restaurant_manager_token}"},
        json={
            "name": "New Hotel",
            "address": "1 New St",
            "city": "Newville",
            "country": "Newland",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_hotel_allowed_for_ops_manager(client: AsyncClient, ops_manager_token: str):
    response = await client.post(
        "/api/v1/hotels/",
        headers={"Authorization": f"Bearer {ops_manager_token}"},
        json={
            "name": "New Hotel",
            "address": "1 New St",
            "city": "Newville",
            "country": "Newland",
        },
    )
    assert response.status_code == 201
