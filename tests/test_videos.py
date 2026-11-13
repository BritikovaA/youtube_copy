from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.main import app
from app.models.user import User


def test_video_upload_requires_authentication(
    client: TestClient,
) -> None:
    response = client.post(
        "/videos/upload",
        data={"title": "Test video"},
        files={
            "file": (
                "video.mp4",
                b"test video content",
                "video/mp4",
            ),
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_moderation_queue_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get("/videos/moderation")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_regular_user_cannot_access_moderation(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/videos/moderation")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_moderator_can_access_moderation_queue(
    client: TestClient,
    moderator_user: User,
    mock_db: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalars.return_value.unique.return_value.all.return_value = []

    mock_db.execute = AsyncMock(return_value=result)

    app.dependency_overrides[get_current_user] = lambda: moderator_user

    response = client.get("/videos/moderation")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []