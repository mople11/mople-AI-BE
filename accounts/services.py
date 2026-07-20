import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from accounts.models import EmailVerificationCode, User
from common.exceptions import ApiError, ErrorCode


def send_email_verification_code(
    *,
    email: str,
    purpose: str,
) -> EmailVerificationCode:
    now = timezone.now()
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = now + timedelta(
        minutes=settings.EMAIL_VERIFICATION_CODE_LIFETIME_MIN
    )

    with transaction.atomic():
        EmailVerificationCode.objects.filter(
            email=email,
            purpose=purpose,
            is_used=False,
        ).update(is_used=True)
        verification = EmailVerificationCode.objects.create(
            email=email,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
        )
        transaction.on_commit(
            lambda: send_mail(
                subject="[어디가남] 이메일 인증번호 안내",
                message=(
                    f"이메일 인증번호는 {code}입니다.\n"
                    f"인증번호는 "
                    f"{settings.EMAIL_VERIFICATION_CODE_LIFETIME_MIN}분 동안 "
                    "유효합니다."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        )

    return verification


def verify_email_verification_code(
    *,
    email: str,
    code: str,
    purpose: str,
    for_update: bool = False,
) -> EmailVerificationCode:
    queryset = EmailVerificationCode.objects.filter(
        email=email,
        code=code,
        purpose=purpose,
    )
    if for_update:
        queryset = queryset.select_for_update()
    verification = queryset.order_by("-expires_at", "-pk").first()

    if verification is None:
        raise ApiError(ErrorCode.CODE_MISMATCH)
    if verification.is_used:
        raise ApiError(ErrorCode.CODE_ALREADY_USED)
    if verification.expires_at <= timezone.now():
        raise ApiError(ErrorCode.CODE_EXPIRED)

    return verification


def send_password_reset_code(*, email: str) -> None:
    if User.objects.filter(email=email).exists():
        send_email_verification_code(
            email=email,
            purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
        )


def reset_password(*, email: str, code: str, new_password: str) -> User:
    with transaction.atomic():
        verification = verify_email_verification_code(
            email=email,
            code=code,
            purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
            for_update=True,
        )
        try:
            user = User.objects.select_for_update().get(email=email)
        except User.DoesNotExist:
            raise ApiError(ErrorCode.CODE_MISMATCH)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        verification.is_used = True
        verification.save(update_fields=["is_used"])

    return user
