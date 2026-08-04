import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from decimal import Decimal

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine, get_db
from app.main import app
from app.models.hotel import Branch, Hotel, RoomType
from app.models.user import User


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_pool_per_test():
    # pytest-asyncio gives each test its own event loop, but app.db.session.engine
    # is a module-level singleton whose asyncpg pool holds connections bound to
    # whichever loop created them. Disposing after every test forces the pool to
    # open fresh connections on the next test's loop instead of reusing stale ones.
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_branch(db_session: AsyncSession) -> Branch:
    hotel = Hotel(name="Test Hotel", address="1 Test St", city="Testville", country="Testland")
    db_session.add(hotel)
    await db_session.flush()

    branch = Branch(hotel_id=hotel.id, name="Main Branch", is_main_branch=True)
    db_session.add(branch)
    await db_session.commit()
    await db_session.refresh(branch)
    return branch


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession) -> User:
    user = User(
        email=f"owner-{uuid.uuid4()}@test.local",
        hashed_password=hash_password("test-password"),
        full_name="Test Owner",
        role="OWNER",
        branch_id=None,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def ops_manager_user(db_session: AsyncSession, seeded_branch: Branch) -> User:
    user = User(
        email=f"ops-{uuid.uuid4()}@test.local",
        hashed_password=hash_password("test-password"),
        full_name="Test Ops Manager",
        role="OPS_MANAGER",
        branch_id=seeded_branch.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def restaurant_manager_user(db_session: AsyncSession, seeded_branch: Branch) -> User:
    user = User(
        email=f"restaurant-{uuid.uuid4()}@test.local",
        hashed_password=hash_password("test-password"),
        full_name="Test Restaurant Manager",
        role="RESTAURANT_MANAGER",
        branch_id=seeded_branch.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_headers(client_login_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {client_login_token}"}


@pytest_asyncio.fixture
async def owner_token(client: AsyncClient, owner_user: User) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": owner_user.email, "password": "test-password"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def ops_manager_token(client: AsyncClient, ops_manager_user: User) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": ops_manager_user.email, "password": "test-password"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def restaurant_manager_token(client: AsyncClient, restaurant_manager_user: User) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": restaurant_manager_user.email, "password": "test-password"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def revenue_manager_user(db_session: AsyncSession, seeded_branch: Branch) -> User:
    user = User(
        email=f"revenue-{uuid.uuid4()}@test.local",
        hashed_password=hash_password("test-password"),
        full_name="Test Revenue Manager",
        role="REVENUE_MANAGER",
        branch_id=seeded_branch.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def revenue_manager_token(client: AsyncClient, revenue_manager_user: User) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": revenue_manager_user.email, "password": "test-password"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def seeded_room_type(db_session: AsyncSession, seeded_branch: Branch) -> RoomType:
    room_type = RoomType(
        branch_id=seeded_branch.id,
        name="Standard",
        base_price=Decimal("100.00"),
        max_occupancy=2,
    )
    db_session.add(room_type)
    await db_session.commit()
    await db_session.refresh(room_type)
    return room_type
