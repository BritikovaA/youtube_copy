import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "payload",
    [
        {
            "email": "invalid-email",
            "password": "password123",
        },
        {
            "email": "user@example.com",
            "password": "short",
        },
        {
            "email": "user@example.com",
            "password": "",
        },
    ],
)
def test_register_validation(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    response = client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {
            "email": "invalid-email",
            "password": "password123",
        },
        {
            "email": "user@example.com",
            "password": "",
        },
        {
            "email": "user@example.com",
            "password": "x" * 129,
        },
    ],
)
def test_login_validation(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    response = client.post(
        "/auth/login",
        json=payload,
    )

    assert response.status_code == 422