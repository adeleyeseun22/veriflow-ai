from httpx import ASGITransport, AsyncClient

from veriflow_api.config import settings
from veriflow_api.main import app


async def test_service_info() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200

    body = response.json()

    assert body["name"] == settings.app_name
    assert body["version"] == settings.api_version
    assert body["environment"] == settings.app_env


async def test_liveness() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
