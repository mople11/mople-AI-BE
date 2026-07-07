from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_not_found_error_uses_common_error_response():
    response = client.get("/api/v1/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "COMMON_404",
            "message": "요청한 리소스를 찾을 수 없습니다.",
        },
    }


def test_validation_error_uses_common_error_response():
    response = client.get("/api/v1/auth/signup/check-id")

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "COMMON_422",
            "message": "요청 값이 올바르지 않습니다.",
        },
    }


def test_required_auth_without_header_returns_common_error_response():
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "AUTH_401",
            "message": "인증이 필요합니다.",
        },
    }
