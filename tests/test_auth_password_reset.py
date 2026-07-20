from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from accounts.models import EmailVerificationCode, User


RESET_REQUEST_URL = "/api/v1/auth/password/reset-request"
RESET_CONFIRM_URL = "/api/v1/auth/password/reset-confirm"
LOGIN_URL = "/api/v1/auth/login"
EMAIL = "traveler@example.com"
CODE = "123456"
OLD_PASSWORD = "old-secure-password-123"
NEW_PASSWORD = "completely-new-password-2048"


def create_user() -> User:
    return User.objects.create_user(
        username="traveler",
        email=EMAIL,
        nickname="여행자",
        password=OLD_PASSWORD,
    )


def create_password_reset_code(**overrides) -> EmailVerificationCode:
    values = {
        "email": EMAIL,
        "code": CODE,
        "purpose": EmailVerificationCode.Purpose.PASSWORD_RESET,
        "expires_at": timezone.now() + timedelta(minutes=5),
    }
    values.update(overrides)
    return EmailVerificationCode.objects.create(**values)


def reset_confirm_payload(**overrides):
    payload = {
        "email": EMAIL,
        "code": CODE,
        "newPw": NEW_PASSWORD,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_password_reset_request_sends_code_for_registered_email(
    api_client,
    django_capture_on_commit_callbacks,
):
    create_user()

    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            RESET_REQUEST_URL,
            {"email": EMAIL},
            format="json",
        )

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"message": "인증번호가 발송되었습니다."},
        "error": None,
    }
    verification = EmailVerificationCode.objects.get()
    assert verification.email == EMAIL
    assert verification.purpose == EmailVerificationCode.Purpose.PASSWORD_RESET
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [EMAIL]
    assert verification.code in mail.outbox[0].body


@pytest.mark.django_db
def test_password_reset_request_hides_unregistered_email(api_client):
    response = api_client.post(
        RESET_REQUEST_URL,
        {"email": "unknown@example.com"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"message": "인증번호가 발송되었습니다."},
        "error": None,
    }
    assert EmailVerificationCode.objects.exists() is False
    assert mail.outbox == []


@pytest.mark.django_db
def test_password_reset_confirm_changes_password_and_allows_login(api_client):
    user = create_user()
    verification = create_password_reset_code()

    response = api_client.post(
        RESET_CONFIRM_URL,
        reset_confirm_payload(),
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"success": True},
        "error": None,
    }
    user.refresh_from_db()
    verification.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert verification.is_used is True

    login_response = api_client.post(
        LOGIN_URL,
        {"id": user.username, "pw": NEW_PASSWORD},
        format="json",
    )
    assert login_response.status_code == 200
    assert login_response.data["success"] is True


@pytest.mark.django_db
def test_password_reset_confirm_rejects_mismatched_code(api_client):
    create_user()
    verification = create_password_reset_code()

    response = api_client.post(
        RESET_CONFIRM_URL,
        reset_confirm_payload(code="000000"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_MISMATCH"
    verification.refresh_from_db()
    assert verification.is_used is False


@pytest.mark.django_db
def test_password_reset_confirm_rejects_expired_code(api_client):
    create_user()
    verification = create_password_reset_code(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    response = api_client.post(
        RESET_CONFIRM_URL,
        reset_confirm_payload(),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_EXPIRED"
    verification.refresh_from_db()
    assert verification.is_used is False


@pytest.mark.django_db
def test_password_reset_confirm_rejects_already_used_code(api_client):
    create_user()
    create_password_reset_code(is_used=True)

    response = api_client.post(
        RESET_CONFIRM_URL,
        reset_confirm_payload(),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_ALREADY_USED"


@pytest.mark.django_db
@pytest.mark.parametrize("new_password", ["1", "traveler-2026"])
def test_password_reset_confirm_rejects_password_policy_violations(
    api_client,
    new_password,
):
    create_user()
    verification = create_password_reset_code()

    response = api_client.post(
        RESET_CONFIRM_URL,
        reset_confirm_payload(newPw=new_password),
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "newPw" in response.data["error"]["details"]
    verification.refresh_from_db()
    assert verification.is_used is False


@pytest.mark.django_db
def test_password_reset_confirm_rejects_reusing_code_after_success(api_client):
    create_user()
    verification = create_password_reset_code()

    first_response = api_client.post(
        RESET_CONFIRM_URL,
        reset_confirm_payload(),
        format="json",
    )
    second_response = api_client.post(
        RESET_CONFIRM_URL,
        reset_confirm_payload(newPw="another-secure-password-4096"),
        format="json",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.data["error"]["code"] == "CODE_ALREADY_USED"
    verification.refresh_from_db()
    assert verification.is_used is True
