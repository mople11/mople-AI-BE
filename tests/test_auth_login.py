from datetime import timedelta

import pytest
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
PASSWORD = "safe-password-123"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="traveler",
        email="traveler@example.com",
        nickname="여행자",
        password=PASSWORD,
    )


def login(api_client, **overrides):
    payload = {"id": "traveler", "pw": PASSWORD}
    payload.update(overrides)
    return api_client.post(LOGIN_URL, payload, format="json")


def test_login_success(api_client, user):
    response = login(api_client)

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["error"] is None
    assert response.data["data"]["accessToken"]
    assert response.data["data"]["refreshToken"]
    assert response.data["data"]["user"] == {
        "id": user.username,
        "nickname": user.nickname,
    }


@pytest.mark.parametrize(
    "credentials",
    [
        {"id": "unknown", "pw": PASSWORD},
        {"id": "traveler", "pw": "wrong-password"},
    ],
)
def test_login_invalid_credentials_use_same_error(api_client, user, credentials):
    response = api_client.post(LOGIN_URL, credentials, format="json")

    assert response.status_code == 401
    assert response.data == {
        "success": False,
        "data": None,
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "아이디 또는 비밀번호가 일치하지 않습니다.",
        },
    }


def test_login_rejects_inactive_user(api_client, user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = login(api_client)

    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_id_longer_than_username_limit(api_client):
    response = login(api_client, id="a" * 151)

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "id" in response.data["error"]["details"]


def test_logout_blacklists_refresh_token(api_client, user):
    login_response = login(api_client)
    access_token = login_response.data["data"]["accessToken"]
    refresh_token = login_response.data["data"]["refreshToken"]

    response = api_client.post(
        LOGOUT_URL,
        {"refreshToken": refresh_token},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 200
    assert response.data == {"success": True, "data": None, "error": None}
    assert BlacklistedToken.objects.filter(token__token=refresh_token).exists()
    with pytest.raises(TokenError):
        RefreshToken(refresh_token)


def test_logout_requires_access_token(api_client, user):
    refresh_token = str(RefreshToken.for_user(user))

    response = api_client.post(
        LOGOUT_URL,
        {"refreshToken": refresh_token},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"


def test_logout_rejects_another_users_refresh_token(api_client, user):
    another_user = User.objects.create_user(
        username="another-traveler",
        email="another@example.com",
        nickname="다른 여행자",
        password=PASSWORD,
    )
    access_token = str(RefreshToken.for_user(user).access_token)
    another_refresh = str(RefreshToken.for_user(another_user))

    response = api_client.post(
        LOGOUT_URL,
        {"refreshToken": another_refresh},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "INVALID_TOKEN"
    assert not BlacklistedToken.objects.filter(token__token=another_refresh).exists()
    assert RefreshToken(another_refresh)


def test_logout_rejects_invalid_refresh_token(api_client, user):
    access_token = str(RefreshToken.for_user(user).access_token)

    response = api_client.post(
        LOGOUT_URL,
        {"refreshToken": "invalid-token"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "INVALID_TOKEN"


def test_logout_rejects_expired_refresh_token(api_client, user):
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh.set_exp(lifetime=timedelta(seconds=-1))

    response = api_client.post(
        LOGOUT_URL,
        {"refreshToken": str(refresh)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "INVALID_TOKEN"


def test_logout_rejects_already_blacklisted_refresh_token(api_client, user):
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh.blacklist()

    response = api_client.post(
        LOGOUT_URL,
        {"refreshToken": str(refresh)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "INVALID_TOKEN"


def test_logout_rejects_missing_refresh_token(api_client, user):
    access_token = str(RefreshToken.for_user(user).access_token)

    response = api_client.post(
        LOGOUT_URL,
        {},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "refreshToken" in response.data["error"]["details"]
