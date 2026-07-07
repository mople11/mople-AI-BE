from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check_returns_common_response():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "UP"},
        "error": None,
    }
