import pytest
from httpx import AsyncClient

from tests.integration.conftest import requires_docker
from app.models.user import User

pytestmark = requires_docker


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, owner_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": owner_user.email, "password": "test-password"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, owner_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": owner_user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.local", "password": "whatever"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token(client: AsyncClient, owner_user: User, owner_token: str):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == owner_user.email
    assert body["role"] == "OWNER"
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
