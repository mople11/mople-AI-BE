from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import EmailVerificationCode, User


SIGNUP_URL = "/api/v1/auth/signup"
CHECK_ID_URL = "/api/v1/auth/signup/check-id"
SIGNUP_CODE = "123456"


def signup_payload(**overrides):
    payload = {
        "id": "traveler",
        "pw": "safe-password-123",
        "pwCheck": "safe-password-123",
        "nickname": "여행자",
        "email": "traveler@example.com",
        "verifyCode": SIGNUP_CODE,
        "agreeTerms": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_signup_success(api_client):
    verification = EmailVerificationCode.objects.create(
        email="traveler@example.com",
        code=SIGNUP_CODE,
        purpose=EmailVerificationCode.Purpose.SIGNUP,
        expires_at=timezone.now() + timedelta(minutes=5),
    )

    response = api_client.post(SIGNUP_URL, signup_payload(), format="json")

    assert response.status_code == 201
    assert response.data["success"] is True
    assert response.data["error"] is None
    assert response.data["data"]["userId"] == "traveler"
    assert response.data["data"]["accessToken"]

    user = User.objects.get(username="traveler")
    assert user.email == "traveler@example.com"
    assert user.nickname == "여행자"
    assert user.agreed_terms_at is not None
    assert user.check_password("safe-password-123")
    verification.refresh_from_db()
    assert verification.is_used is True


@pytest.mark.django_db
def test_signup_duplicate_id(api_client):
    User.objects.create_user(
        username="traveler",
        email="existing@example.com",
        nickname="기존 사용자",
        password="safe-password-123",
    )

    response = api_client.post(SIGNUP_URL, signup_payload(), format="json")

    assert response.status_code == 409
    assert response.data == {
        "success": False,
        "data": None,
        "error": {
            "code": "DUPLICATE_ID",
            "message": "이미 사용 중인 아이디입니다.",
        },
    }


@pytest.mark.django_db
def test_signup_duplicate_email(api_client):
    User.objects.create_user(
        username="existing-traveler",
        email="traveler@example.com",
        nickname="기존 사용자",
        password="safe-password-123",
    )

    response = api_client.post(SIGNUP_URL, signup_payload(), format="json")

    assert response.status_code == 409
    assert response.data == {
        "success": False,
        "data": None,
        "error": {
            "code": "DUPLICATE_EMAIL",
            "message": "이미 사용 중인 이메일입니다.",
        },
    }


@pytest.mark.django_db
def test_signup_duplicate_nickname(api_client):
    User.objects.create_user(
        username="existing-nickname-user",
        email="existing-nickname@example.com",
        nickname="여행자",
        password="safe-password-123",
    )

    response = api_client.post(SIGNUP_URL, signup_payload(), format="json")

    assert response.status_code == 409
    assert response.data == {
        "success": False,
        "data": None,
        "error": {
            "code": "NICKNAME_DUPLICATE",
            "message": "이미 사용 중인 닉네임입니다.",
        },
    }


@pytest.mark.django_db
def test_check_id_duplicate(api_client):
    User.objects.create_user(
        username="traveler",
        email="existing@example.com",
        nickname="기존 사용자",
        password="safe-password-123",
    )

    response = api_client.get(CHECK_ID_URL, {"id": "traveler"})

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"available": False},
        "error": None,
    }


@pytest.mark.django_db
def test_check_id_available(api_client):
    response = api_client.get(CHECK_ID_URL, {"id": "new-traveler"})

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"available": True},
        "error": None,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query_params",
    [None, {"id": ""}, {"id": "   "}],
)
def test_check_id_rejects_missing_or_blank_id(api_client, query_params):
    response = api_client.get(CHECK_ID_URL, query_params or {})

    assert response.status_code == 422
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "COMMON_422"
    assert "id" in response.data["error"]["details"]


@pytest.mark.django_db
def test_signup_password_mismatch(api_client):
    response = api_client.post(
        SIGNUP_URL,
        signup_payload(pwCheck="different-password"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "PASSWORD_MISMATCH"


@pytest.mark.django_db
def test_signup_rejects_weak_password(api_client):
    response = api_client.post(
        SIGNUP_URL,
        signup_payload(pw="1", pwCheck="1"),
        format="json",
    )

    assert response.status_code == 422
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "COMMON_422"
    assert "pw" in response.data["error"]["details"]


@pytest.mark.django_db
def test_signup_terms_not_agreed(api_client):
    response = api_client.post(
        SIGNUP_URL,
        signup_payload(agreeTerms=False),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "TERMS_NOT_AGREED"


@pytest.mark.django_db
def test_signup_code_mismatch(api_client):
    response = api_client.post(
        SIGNUP_URL,
        signup_payload(verifyCode="wrong-code"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "CODE_MISMATCH"


@pytest.mark.django_db
def test_signup_rejects_expired_code(api_client):
    verification = EmailVerificationCode.objects.create(
        email="traveler@example.com",
        code=SIGNUP_CODE,
        purpose=EmailVerificationCode.Purpose.SIGNUP,
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    response = api_client.post(SIGNUP_URL, signup_payload(), format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_EXPIRED"
    assert User.objects.exists() is False
    verification.refresh_from_db()
    assert verification.is_used is False


@pytest.mark.django_db
def test_signup_rejects_already_used_code(api_client):
    EmailVerificationCode.objects.create(
        email="traveler@example.com",
        code=SIGNUP_CODE,
        purpose=EmailVerificationCode.Purpose.SIGNUP,
        expires_at=timezone.now() + timedelta(minutes=5),
        is_used=True,
    )

    response = api_client.post(SIGNUP_URL, signup_payload(), format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_ALREADY_USED"
    assert User.objects.exists() is False


@pytest.mark.django_db
def test_signup_validation_failure_does_not_consume_code(api_client):
    verification = EmailVerificationCode.objects.create(
        email="traveler@example.com",
        code=SIGNUP_CODE,
        purpose=EmailVerificationCode.Purpose.SIGNUP,
        expires_at=timezone.now() + timedelta(minutes=5),
    )

    response = api_client.post(
        SIGNUP_URL,
        signup_payload(pwCheck="different-password"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "PASSWORD_MISMATCH"
    verification.refresh_from_db()
    assert verification.is_used is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "invalid_field"),
    [
        ({"id": ""}, "id"),
        ({"id": "   "}, "id"),
        ({"id": "a" * 151}, "id"),
        ({"id": "invalid id"}, "id"),
        ({"nickname": ""}, "nickname"),
        ({"nickname": "가" * 51}, "nickname"),
        ({"email": "not-an-email"}, "email"),
    ],
)
def test_signup_rejects_invalid_field_boundaries(
    api_client,
    overrides,
    invalid_field,
):
    response = api_client.post(
        SIGNUP_URL,
        signup_payload(**overrides),
        format="json",
    )

    assert response.status_code == 422
    assert response.data["success"] is False
    assert response.data["error"]["code"] == "COMMON_422"
    assert invalid_field in response.data["error"]["details"]
