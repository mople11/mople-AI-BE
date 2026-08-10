import secrets
from datetime import timedelta
from hashlib import sha256

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
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


def find_or_create_social_user(
    *,
    provider: str,
    provider_id: str,
    email: str,
    nickname: str,
) -> User:
    try:
        return User.objects.get(provider=provider, provider_id=provider_id)
    except User.DoesNotExist:
        pass

    if User.objects.filter(email=email).exists():
        raise ApiError(ErrorCode.SOCIAL_EMAIL_CONFLICT)

    username = f"{provider}_{provider_id}"
    username_max_length = User._meta.get_field("username").max_length
    if len(username) > username_max_length:
        username = f"{provider}_{sha256(provider_id.encode()).hexdigest()}"

    nickname_max_length = User._meta.get_field("nickname").max_length
    base_nickname = nickname[:nickname_max_length]
    suffix = 0

    while True:
        tag = "" if suffix == 0 else f"_{suffix}"
        unique_nickname = f"{base_nickname[: nickname_max_length - len(tag)]}{tag}"
        if User.objects.filter(nickname=unique_nickname).exists():
            suffix += 1
            continue

        user = User(
            username=username,
            email=email,
            nickname=unique_nickname,
            provider=provider,
            provider_id=provider_id,
        )
        user.set_unusable_password()
        try:
            user.save()
        except IntegrityError:
            existing = User.objects.filter(
                provider=provider, provider_id=provider_id
            ).first()
            if existing is not None:
                return existing
            if User.objects.filter(email=user.email).exists():
                raise ApiError(ErrorCode.SOCIAL_EMAIL_CONFLICT)
            if User.objects.filter(nickname=user.nickname).exists():
                suffix += 1
                continue
            if User.objects.filter(username=user.username).exists():
                raise ApiError(ErrorCode.DUPLICATE_ID)
            raise

        return user
