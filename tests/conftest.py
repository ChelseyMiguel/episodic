"""
Test configuration and fixtures.

Uses SQLite in-memory database for isolation and speed.
pytest-asyncio handles async test functions.
httpx AsyncClient is used for async HTTP calls against the ASGI app.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.main import app

# SQLite in-memory async URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Use a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for each test, rolled back after."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient with the test DB injected."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Helper fixtures for common user creation
@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """Create an admin user and return its access token."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    async with TestSessionLocal() as session:
        user = User(
            email="admin@test.com",
            hashed_password=hash_password("adminpass123"),
            display_name="Test Admin",
            role=UserRole.admin,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "adminpass123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def editor_token(client: AsyncClient) -> str:
    """Create an editor user and return its access token."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    async with TestSessionLocal() as session:
        user = User(
            email="editor@test.com",
            hashed_password=hash_password("editorpass123"),
            display_name="Test Editor",
            role=UserRole.editor,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "email": "editor@test.com",
        "password": "editorpass123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def contributor_token(client: AsyncClient) -> str:
    """Create a contributor user and return its access token."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    async with TestSessionLocal() as session:
        user = User(
            email="contributor@test.com",
            hashed_password=hash_password("contribpass123"),
            display_name="Test Contributor",
            role=UserRole.contributor,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "email": "contributor@test.com",
        "password": "contribpass123",
    })
    return resp.json()["access_token"]
