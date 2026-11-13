from fastapi.testclient import TestClient


def test_get_me_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401


def test_get_me_rejects_invalid_token(
    client: TestClient,
) -> None:
    response = client.get(
        "/users/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


def test_get_me_returns_authenticated_user(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/users/me")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["email"] == "user@test.com"
    assert data["role"] == "user"


def test_subscriptions_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get("/users/subscriptions")

    assert response.status_code == 401