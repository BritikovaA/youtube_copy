from fastapi.testclient import TestClient


def test_comment_rejects_empty_text(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/videos/1/comments",
        json={
            "text": "",
        },
    )

    assert response.status_code == 422


def test_comment_rejects_whitespace_only_text(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/videos/1/comments",
        json={
            "text": "   ",
        },
    )

    assert response.status_code == 422


def test_video_endpoint_rejects_invalid_id(
    client: TestClient,
) -> None:
    response = client.get("/videos/not-an-integer")

    assert response.status_code == 422