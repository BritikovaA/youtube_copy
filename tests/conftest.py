import os
from collections.abc import AsyncGenerator, Generator
from typing import cast
from unittest.mock import AsyncMock
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "youtube_copy_test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("MINIO_ACCESS_KEY", "test-access-key")
os.environ.setdefault("MINIO_SECRET_KEY", "test-secret-key")

from app.core.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def regular_user() -> User:
    return User(
        id=1,
        email="user@test.com",
        hashed_password="hashed-password",
        role=UserRole.USER,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def moderator_user() -> User:
    return User(
        id=2,
        email="moderator@test.com",
        hashed_password="hashed-password",
        role=UserRole.MODERATOR,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def admin_user() -> User:
    return User(
        id=3,
        email="admin@test.com",
        hashed_password="hashed-password",
        role=UserRole.ADMIN,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def client(
    mock_db: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    from app import main

    monkeypatch.setattr(
        main,
        "ensure_bucket_exists",
        AsyncMock(),
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield cast(AsyncSession, mock_db)

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(
    client: TestClient,
    regular_user: User,
) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: regular_user
    return client