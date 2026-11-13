from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "message": "YouTube Copy API is running",
    }


def test_documentation_page(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_openapi_schema(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/health" in paths
    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/users/me" in paths
    assert "/videos" in paths
    assert "/videos/upload" in paths