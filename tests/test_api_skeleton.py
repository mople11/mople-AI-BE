import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


PUBLIC_ENDPOINTS = [
    ("GET", "/api/v1/health", None),
    (
        "POST",
        "/api/v1/auth/signup",
        {
            "id": "hawon",
            "pw": "password",
            "pwCheck": "password",
            "nickname": "여행자",
            "email": "hawon@example.com",
            "verifyCode": "123456",
            "agreeTerms": True,
        },
    ),
    ("GET", "/api/v1/auth/signup/check-id?id=hawon", None),
    ("POST", "/api/v1/auth/login", {"id": "hawon", "pw": "password"}),
    (
        "POST",
        "/api/v1/auth/login/social",
        {"provider": "google", "oauthToken": "mock-oauth-token"},
    ),
    (
        "POST",
        "/api/v1/auth/login/social",
        {"provider": "kakao", "oauthToken": "mock-oauth-token"},
    ),
    ("POST", "/api/v1/auth/email/verify-code", {"email": "hawon@example.com"}),
    (
        "POST",
        "/api/v1/auth/email/verify-confirm",
        {"email": "hawon@example.com", "code": "123456"},
    ),
    ("POST", "/api/v1/auth/password/reset-request", {"email": "hawon@example.com"}),
    (
        "POST",
        "/api/v1/auth/password/reset-confirm",
        {"email": "hawon@example.com", "code": "123456", "newPw": "new-password"},
    ),
]

AUTH_ENDPOINTS = [
    ("POST", "/api/v1/auth/logout", None),
]


def request(method: str, path: str, body: dict | None = None, authenticated: bool = False):
    headers = {"Authorization": "Bearer mock-token"} if authenticated else None
    return client.request(method, path, json=body, headers=headers)


@pytest.mark.parametrize(("method", "path", "body"), PUBLIC_ENDPOINTS)
def test_public_skeleton_endpoints_follow_common_response(
    method: str,
    path: str,
    body: dict | None,
):
    response = request(method, path, body)
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert "data" in body
    assert body["error"] is None


@pytest.mark.parametrize(("method", "path", "body"), AUTH_ENDPOINTS)
def test_auth_skeleton_endpoints_follow_common_response_with_header(
    method: str,
    path: str,
    body: dict | None,
):
    response = request(method, path, body, authenticated=True)
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert "data" in body
    assert body["error"] is None


@pytest.mark.parametrize(("method", "path", "body"), AUTH_ENDPOINTS)
def test_auth_skeleton_endpoints_require_authorization_header(
    method: str,
    path: str,
    body: dict | None,
):
    response = request(method, path, body)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_401"


def test_social_login_rejects_unsupported_provider():
    response = request(
        "POST",
        "/api/v1/auth/login/social",
        {"provider": "github", "oauthToken": "mock-oauth-token"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "COMMON_422"
