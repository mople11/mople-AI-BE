import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone

from accounts.models import EmailVerificationCode


SEND_CODE_URL = "/api/v1/auth/email/verify-code"
VERIFY_CODE_URL = "/api/v1/auth/email/verify-confirm"
EMAIL = "traveler@example.com"
CODE = "123456"


def verification_payload(**overrides):
    payload = {
        "email": EMAIL,
        "code": CODE,
        "purpose": EmailVerificationCode.Purpose.SIGNUP,
    }
    payload.update(overrides)
    return payload


def create_verification_code(**overrides):
    values = {
        "email": EMAIL,
        "code": CODE,
        "purpose": EmailVerificationCode.Purpose.SIGNUP,
        "expires_at": timezone.now() + timedelta(minutes=5),
    }
    values.update(overrides)
    return EmailVerificationCode.objects.create(**values)


@pytest.mark.django_db
def test_send_email_verification_code(
    api_client,
    django_capture_on_commit_callbacks,
):
    requested_at = timezone.now()

    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            SEND_CODE_URL,
            {
                "email": EMAIL,
                "purpose": EmailVerificationCode.Purpose.SIGNUP,
            },
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
    assert verification.purpose == EmailVerificationCode.Purpose.SIGNUP
    assert re.fullmatch(r"[0-9]{6}", verification.code)
    assert verification.is_used is False
    expected_expiry = requested_at + timedelta(
        minutes=settings.EMAIL_VERIFICATION_CODE_LIFETIME_MIN
    )
    assert expected_expiry <= verification.expires_at <= expected_expiry + timedelta(
        seconds=2
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [EMAIL]
    assert verification.code in mail.outbox[0].body


@pytest.mark.django_db
def test_resending_code_invalidates_previous_unused_code(api_client):
    previous = create_verification_code(code="654321")

    response = api_client.post(
        SEND_CODE_URL,
        {
            "email": EMAIL,
            "purpose": EmailVerificationCode.Purpose.SIGNUP,
        },
        format="json",
    )

    assert response.status_code == 200
    previous.refresh_from_db()
    assert previous.is_used is True
    assert EmailVerificationCode.objects.filter(
        email=EMAIL,
        purpose=EmailVerificationCode.Purpose.SIGNUP,
        is_used=False,
    ).count() == 1


@pytest.mark.django_db(transaction=True)
def test_send_code_persists_when_email_delivery_fails_after_commit(api_client):
    previous = create_verification_code(code="654321")

    with patch("accounts.services.send_mail", side_effect=RuntimeError("mail failed")):
        response = api_client.post(
            SEND_CODE_URL,
            {
                "email": EMAIL,
                "purpose": EmailVerificationCode.Purpose.SIGNUP,
            },
            format="json",
        )

    assert response.status_code == 500
    assert response.data["error"]["code"] == "COMMON_500"
    previous.refresh_from_db()
    assert previous.is_used is True
    assert EmailVerificationCode.objects.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "purpose": "signup"},
        {"email": EMAIL, "purpose": "unknown"},
        {"purpose": "signup"},
    ],
)
def test_send_code_rejects_invalid_request(api_client, payload):
    response = api_client.post(SEND_CODE_URL, payload, format="json")

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


@pytest.mark.django_db
def test_verify_email_code_success_does_not_consume_code(api_client):
    verification = create_verification_code()

    first_response = api_client.post(
        VERIFY_CODE_URL,
        verification_payload(),
        format="json",
    )
    second_response = api_client.post(
        VERIFY_CODE_URL,
        verification_payload(),
        format="json",
    )

    assert first_response.status_code == 200
    assert first_response.data == {
        "success": True,
        "data": {"message": "인증번호가 확인되었습니다."},
        "error": None,
    }
    assert second_response.status_code == 200
    verification.refresh_from_db()
    assert verification.is_used is False


@pytest.mark.django_db
def test_verify_email_code_mismatch(api_client):
    create_verification_code()

    response = api_client.post(
        VERIFY_CODE_URL,
        verification_payload(code="000000"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_MISMATCH"


@pytest.mark.django_db
def test_verify_email_code_expired(api_client):
    create_verification_code(expires_at=timezone.now() - timedelta(seconds=1))

    response = api_client.post(
        VERIFY_CODE_URL,
        verification_payload(),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_EXPIRED"


@pytest.mark.django_db
def test_verify_email_code_already_used(api_client):
    create_verification_code(is_used=True)

    response = api_client.post(
        VERIFY_CODE_URL,
        verification_payload(),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "CODE_ALREADY_USED"


@pytest.mark.django_db
def test_verify_email_code_rejects_invalid_code_format(api_client):
    response = api_client.post(
        VERIFY_CODE_URL,
        verification_payload(code="abc"),
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "code" in response.data["error"]["details"]
