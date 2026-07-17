from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import EmailVerificationCode, User
from accounts.services import verify_email_verification_code
from common.exceptions import ApiError, ErrorCode


class SendEmailVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="인증번호를 받을 이메일 주소")
    purpose = serializers.ChoiceField(
        choices=EmailVerificationCode.Purpose.choices,
        help_text="인증 목적(signup 또는 password_reset)",
    )


class VerifyEmailVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="인증번호를 발급받은 이메일 주소")
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        validators=[
            RegexValidator(
                regex=r"^[0-9]{6}$",
                message="인증번호는 6자리 숫자여야 합니다.",
            )
        ],
        help_text="이메일로 전달받은 6자리 인증번호",
    )
    purpose = serializers.ChoiceField(
        choices=EmailVerificationCode.Purpose.choices,
        help_text="인증 목적(signup 또는 password_reset)",
    )


class SignupSerializer(serializers.Serializer):
    id = serializers.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        help_text="로그인에 사용할 아이디(최대 150자)",
    )
    pw = serializers.CharField(
        write_only=True,
        help_text="Django 비밀번호 정책을 통과해야 하는 비밀번호",
    )
    pwCheck = serializers.CharField(
        write_only=True,
        help_text="pw와 동일하게 입력하는 비밀번호 확인 값",
    )
    nickname = serializers.CharField(
        max_length=50,
        help_text="서비스에 표시할 닉네임(최대 50자)",
    )
    email = serializers.EmailField(help_text="중복되지 않는 유효한 이메일 주소")
    verifyCode = serializers.CharField(
        write_only=True,
        help_text="이메일로 전달받은 회원가입 인증번호",
    )
    agreeTerms = serializers.BooleanField(
        help_text="이용약관 동의 여부. 회원가입하려면 true여야 합니다.",
    )

    def validate_id(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise ApiError(ErrorCode.DUPLICATE_ID)
        return value

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise ApiError(ErrorCode.DUPLICATE_EMAIL)
        return value

    def validate_agreeTerms(self, value: bool) -> bool:
        if not value:
            raise ApiError(ErrorCode.TERMS_NOT_AGREED)
        return value

    def validate(self, attrs):
        if attrs["pw"] != attrs["pwCheck"]:
            raise ApiError(ErrorCode.PASSWORD_MISMATCH)

        user = User(
            username=attrs["id"],
            email=attrs["email"],
            nickname=attrs["nickname"],
        )
        try:
            validate_password(attrs["pw"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"pw": exc.messages}) from exc

        verify_email_verification_code(
            email=attrs["email"],
            code=attrs["verifyCode"],
            purpose=EmailVerificationCode.Purpose.SIGNUP,
        )

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("pw")
        validated_data.pop("pwCheck")
        verification_code = validated_data.pop("verifyCode")
        validated_data.pop("agreeTerms")

        user = User(
            username=validated_data["id"],
            email=validated_data["email"],
            nickname=validated_data["nickname"],
            agreed_terms_at=timezone.now(),
        )
        user.set_password(password)
        try:
            with transaction.atomic():
                verification = verify_email_verification_code(
                    email=user.email,
                    code=verification_code,
                    purpose=EmailVerificationCode.Purpose.SIGNUP,
                    for_update=True,
                )
                user.save()
                verification.is_used = True
                verification.save(update_fields=["is_used"])
        except IntegrityError:
            if User.objects.filter(username=user.username).exists():
                raise ApiError(ErrorCode.DUPLICATE_ID)
            if User.objects.filter(email=user.email).exists():
                raise ApiError(ErrorCode.DUPLICATE_EMAIL)
            raise
        return user


class CheckIdSerializer(serializers.Serializer):
    id = serializers.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        help_text="중복 여부를 확인할 로그인 아이디",
    )
