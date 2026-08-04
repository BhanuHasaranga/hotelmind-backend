import pytest
from httpx import AsyncClient

from tests.integration.conftest import requires_docker
from app.models.hotel import Branch

pytestmark = requires_docker


@pytest.mark.asyncio
async def test_list_departments_requires_auth(client: AsyncClient, seeded_branch: Branch):
    response = await client.get(
        "/api/v1/staff/departments", params={"branch_id": str(seeded_branch.id)}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_department_forbidden_for_restaurant_manager(
    client: AsyncClient, restaurant_manager_token: str, seeded_branch: Branch
):
    response = await client.post(
        "/api/v1/staff/departments",
        headers={"Authorization": f"Bearer {restaurant_manager_token}"},
        json={"branch_id": str(seeded_branch.id), "name": "Housekeeping"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_department_allowed_for_ops_manager(
    client: AsyncClient, ops_manager_token: str, seeded_branch: Branch
):
    response = await client.post(
        "/api/v1/staff/departments",
        headers={"Authorization": f"Bearer {ops_manager_token}"},
        json={"branch_id": str(seeded_branch.id), "name": "Housekeeping"},
    )
    assert response.status_code == 201
