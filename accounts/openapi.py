from rest_framework import serializers


class AuthUserSerializer(serializers.Serializer):
    id = serializers.CharField(help_text="로그인 아이디")
    nickname = serializers.CharField(help_text="사용자 닉네임")


class AuthTokenDataSerializer(serializers.Serializer):
    accessToken = serializers.CharField(help_text="API 인증에 사용할 JWT 액세스 토큰")
    refreshToken = serializers.CharField(
        help_text="액세스 토큰 재발급용 JWT 리프레시 토큰"
    )
    user = AuthUserSerializer()


class AuthTokenSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = AuthTokenDataSerializer()
    error = serializers.JSONField(allow_null=True)


class LogoutSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField(allow_null=True)


class SignupDataSerializer(serializers.Serializer):
    userId = serializers.CharField(help_text="가입한 사용자의 로그인 아이디")
    accessToken = serializers.CharField(help_text="API 인증에 사용할 JWT 액세스 토큰")


class SignupSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = SignupDataSerializer()
    error = serializers.JSONField(allow_null=True)


class CheckIdDataSerializer(serializers.Serializer):
    available = serializers.BooleanField(
        help_text="사용 가능한 아이디이면 true, 이미 사용 중이면 false"
    )


class CheckIdSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = CheckIdDataSerializer()
    error = serializers.JSONField(allow_null=True)


class SendEmailVerificationCodeDataSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="인증번호 발송 결과 메시지")


class SendEmailVerificationCodeSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = SendEmailVerificationCodeDataSerializer()
    error = serializers.JSONField(allow_null=True)


class VerifyEmailVerificationCodeDataSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="인증번호 확인 결과 메시지")


class VerifyEmailVerificationCodeSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = VerifyEmailVerificationCodeDataSerializer()
    error = serializers.JSONField(allow_null=True)


class PasswordResetRequestDataSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="비밀번호 재설정 인증번호 발송 결과")


class PasswordResetRequestSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = PasswordResetRequestDataSerializer()
    error = serializers.JSONField(allow_null=True)


class PasswordResetConfirmDataSerializer(serializers.Serializer):
    success = serializers.BooleanField(help_text="비밀번호 재설정 성공 여부")


class PasswordResetConfirmSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = PasswordResetConfirmDataSerializer()
    error = serializers.JSONField(allow_null=True)


class ApiErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField(help_text="클라이언트가 분기 처리할 에러 코드")
    message = serializers.CharField(help_text="사용자에게 표시할 수 있는 에러 메시지")
    details = serializers.DictField(
        required=False,
        help_text="COMMON_422 응답에 포함되는 필드별 상세 오류",
    )


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = ApiErrorDetailSerializer()
