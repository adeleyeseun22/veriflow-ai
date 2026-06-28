from fastapi.testclient import TestClient

from veriflow_api.main import app


def test_service_info() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "VeriFlow AI API"
    assert body["version"] == "0.1.0"


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
