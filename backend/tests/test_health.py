"""Health route."""

from app.main import app
from fastapi.testclient import TestClient


def test_health() -> None:
    """GET /api/health returns a fixed ok payload."""
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
