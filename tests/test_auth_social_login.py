from unittest.mock import Mock, patch

import pytest
import requests

from accounts.google import verify_google_id_token
from accounts.kakao import verify_kakao_token
from accounts.models import User
from common.exceptions import ApiError


SOCIAL_LOGIN_URL = "/api/v1/auth/login/social"


def social_login(api_client, **overrides):
    payload = {"provider": "google", "oauthToken": "token"}
    payload.update(overrides)
    return api_client.post(SOCIAL_LOGIN_URL, payload, format="json")


@pytest.fixture
def google_profile():
    return {
        "provider_id": "1029384756",
        "email": "traveler@example.com",
        "nickname": "여행자",
    }


@pytest.fixture
def kakao_profile():
    return {
        "provider_id": "998877",
        "email": "traveler@example.com",
        "nickname": "여행자",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {
            "sub": "1029384756",
            "email": "traveler@example.com",
            "email_verified": False,
        },
        {"email": "traveler@example.com", "email_verified": True},
        {"sub": "1029384756", "email_verified": True},
    ],
)
@patch("accounts.google.id_token.verify_oauth2_token")
def test_google_token_rejects_untrusted_or_incomplete_claims(mock_verify, payload):
    mock_verify.return_value = payload

    with pytest.raises(ApiError) as exc_info:
        verify_google_id_token("id-token")

    assert exc_info.value.error_code.value[0] == "OAUTH_FAILED"


@patch("accounts.google.id_token.verify_oauth2_token")
def test_google_token_returns_verified_profile(mock_verify):
    mock_verify.return_value = {
        "sub": "1029384756",
        "email": "traveler@example.com",
        "email_verified": True,
        "name": "여행자",
    }

    profile = verify_google_id_token("id-token")

    assert profile == {
        "provider_id": "1029384756",
        "email": "traveler@example.com",
        "nickname": "여행자",
    }


@patch("accounts.google.id_token.verify_oauth2_token")
def test_google_token_verification_error_returns_oauth_failed(mock_verify):
    mock_verify.side_effect = ValueError("wrong audience")

    with pytest.raises(ApiError) as exc_info:
        verify_google_id_token("id-token")

    assert exc_info.value.error_code.value[0] == "OAUTH_FAILED"


@pytest.mark.parametrize(
    "response",
    [
        Mock(status_code=200, json=Mock(side_effect=ValueError("invalid json"))),
        Mock(status_code=200, json=Mock(return_value={})),
        Mock(status_code=200, json=Mock(return_value=[])),
    ],
)
@patch("accounts.kakao.requests.get")
def test_kakao_token_rejects_invalid_response(mock_get, response):
    mock_get.return_value = response

    with pytest.raises(ApiError) as exc_info:
        verify_kakao_token("access-token")

    assert exc_info.value.error_code.value[0] == "OAUTH_FAILED"


@patch("accounts.kakao.requests.get")
def test_kakao_token_network_error_returns_oauth_failed(mock_get):
    mock_get.side_effect = requests.Timeout

    with pytest.raises(ApiError) as exc_info:
        verify_kakao_token("access-token")

    assert exc_info.value.error_code.value[0] == "OAUTH_FAILED"


@patch("accounts.views.verify_google_id_token")
def test_google_login_creates_new_user(mock_verify, api_client, db, google_profile):
    mock_verify.return_value = google_profile

    response = social_login(api_client, provider="google", oauthToken="valid-id-token")

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["error"] is None
    assert response.data["data"]["accessToken"]
    assert response.data["data"]["refreshToken"]
    assert response.data["data"]["user"]["nickname"] == "여행자"

    user = User.objects.get(email="traveler@example.com")
    assert user.provider == User.Provider.GOOGLE
    assert user.provider_id == "1029384756"
    assert response.data["data"]["user"]["id"] == user.username
    assert not user.has_usable_password()


@patch("accounts.views.verify_google_id_token")
def test_google_login_returns_existing_social_user(
    mock_verify, api_client, db, google_profile
):
    mock_verify.return_value = google_profile
    existing = User.objects.create(
        username="google_1029384756",
        email="traveler@example.com",
        nickname="여행자",
        provider=User.Provider.GOOGLE,
        provider_id="1029384756",
    )

    response = social_login(api_client, provider="google", oauthToken="valid-id-token")

    assert response.status_code == 200
    assert response.data["data"]["user"]["id"] == existing.username
    assert User.objects.filter(email="traveler@example.com").count() == 1


@patch("accounts.views.verify_google_id_token")
def test_google_login_invalid_token_returns_oauth_failed(mock_verify, api_client, db):
    from common.exceptions import ApiError, ErrorCode

    mock_verify.side_effect = ApiError(ErrorCode.OAUTH_FAILED)

    response = social_login(api_client, provider="google", oauthToken="invalid-token")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "OAUTH_FAILED"


@patch("accounts.views.verify_google_id_token")
def test_google_login_email_conflict_with_existing_local_account(
    mock_verify, api_client, db, google_profile
):
    mock_verify.return_value = google_profile
    User.objects.create_user(
        username="traveler",
        email="traveler@example.com",
        nickname="여행자",
        password="safe-password-123",
    )

    response = social_login(api_client, provider="google", oauthToken="valid-id-token")

    assert response.status_code == 409
    assert response.data["error"]["code"] == "SOCIAL_EMAIL_CONFLICT"


@patch("accounts.views.verify_kakao_token")
def test_kakao_login_creates_new_user(mock_verify, api_client, db, kakao_profile):
    mock_verify.return_value = kakao_profile

    response = social_login(api_client, provider="kakao", oauthToken="kakao-access-token")

    assert response.status_code == 200
    user = User.objects.get(email="traveler@example.com")
    assert user.provider == User.Provider.KAKAO
    assert user.provider_id == "998877"


@patch("accounts.kakao.requests.get")
def test_kakao_login_missing_email_still_signs_up_with_placeholder_email(
    mock_get, api_client, db
):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"id": 1029384, "kakao_account": {}}

    response = social_login(api_client, provider="kakao", oauthToken="kakao-access-token")

    assert response.status_code == 200
    user = User.objects.get(provider=User.Provider.KAKAO, provider_id="1029384")
    assert user.email == "kakao_1029384@users.eodiganam.local"
    assert user.nickname
    assert not user.has_usable_password()


@patch("accounts.kakao.requests.get")
def test_kakao_login_missing_email_and_nickname_reuses_same_placeholder(
    mock_get, api_client, db
):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"id": 1029384, "kakao_account": {}}

    social_login(api_client, provider="kakao", oauthToken="kakao-access-token")
    response = social_login(api_client, provider="kakao", oauthToken="kakao-access-token")

    assert response.status_code == 200
    assert User.objects.filter(provider=User.Provider.KAKAO, provider_id="1029384").count() == 1


@patch("accounts.kakao.requests.get")
def test_kakao_login_api_failure_returns_oauth_failed(mock_get, api_client, db):
    mock_get.return_value.status_code = 401
    mock_get.return_value.json.return_value = {}

    response = social_login(api_client, provider="kakao", oauthToken="invalid-token")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "OAUTH_FAILED"


def test_social_login_rejects_unsupported_provider(api_client, db):
    response = social_login(api_client, provider="github", oauthToken="token")

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "provider" in response.data["error"]["details"]
