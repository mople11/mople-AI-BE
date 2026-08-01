from django.contrib.auth import authenticate
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.google import verify_google_id_token
from accounts.kakao import verify_kakao_token
from accounts.models import User
from accounts.openapi import (
    AuthTokenSuccessResponseSerializer,
    CheckIdSuccessResponseSerializer,
    ErrorResponseSerializer,
    LogoutSuccessResponseSerializer,
    PasswordResetConfirmSuccessResponseSerializer,
    PasswordResetRequestSuccessResponseSerializer,
    SendEmailVerificationCodeSuccessResponseSerializer,
    SignupSuccessResponseSerializer,
    VerifyEmailVerificationCodeSuccessResponseSerializer,
)
from accounts.serializers import (
    CheckIdSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SendEmailVerificationCodeSerializer,
    SignupSerializer,
    SocialLoginSerializer,
    VerifyEmailVerificationCodeSerializer,
)
from accounts.services import (
    find_or_create_social_user,
    reset_password,
    send_email_verification_code,
    send_password_reset_code,
    verify_email_verification_code,
)
from common.exceptions import ApiError, ErrorCode
from common.response import ApiResponse


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="로그인",
        description=(
            "아이디와 비밀번호로 사용자를 인증하고 JWT access token과 "
            "refresh token을 발급합니다."
        ),
        tags=["Auth"],
        auth=[],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=AuthTokenSuccessResponseSerializer,
                description="로그인 성공",
                examples=[
                    OpenApiExample(
                        "로그인 성공",
                        value={
                            "success": True,
                            "data": {
                                "accessToken": "eyJ...",
                                "refreshToken": "eyJ...",
                                "user": {"id": "traveler", "nickname": "여행자"},
                            },
                            "error": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="아이디 또는 비밀번호 불일치, 비활성 계정",
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="필수 필드 누락 또는 형식 검증 실패",
            ),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["id"],
            password=serializer.validated_data["pw"],
        )
        if user is None:
            raise ApiError(ErrorCode.INVALID_CREDENTIALS)

        refresh = RefreshToken.for_user(user)
        return ApiResponse(
            data={
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
                "user": {
                    "id": user.username,
                    "nickname": user.nickname,
                },
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="로그아웃",
        description=(
            "유효한 access token으로 인증한 뒤 전달받은 refresh token을 "
            "블랙리스트에 등록합니다."
        ),
        tags=["Auth"],
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(
                response=LogoutSuccessResponseSerializer,
                description="로그아웃 성공",
                examples=[
                    OpenApiExample(
                        "로그아웃 성공",
                        value={"success": True, "data": None, "error": None},
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="유효하지 않거나 이미 블랙리스트에 등록된 refresh token",
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="access token 누락 또는 인증 실패",
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="refreshToken 필드 누락 또는 형식 검증 실패",
            ),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh = RefreshToken(serializer.validated_data["refreshToken"])
        except TokenError as exc:
            raise ApiError(ErrorCode.INVALID_TOKEN) from exc

        if refresh.get("user_id") != str(request.user.pk):
            raise ApiError(ErrorCode.INVALID_TOKEN)

        refresh.blacklist()
        return ApiResponse()


class SocialLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="소셜 로그인",
        description=(
            "Google ID Token 또는 Kakao 액세스 토큰을 검증해 사용자를 조회하거나 "
            "신규 생성하고 JWT access token과 refresh token을 발급합니다."
        ),
        tags=["Auth"],
        auth=[],
        request=SocialLoginSerializer,
        responses={
            200: OpenApiResponse(
                response=AuthTokenSuccessResponseSerializer,
                description="소셜 로그인 성공",
                examples=[
                    OpenApiExample(
                        "소셜 로그인 성공",
                        value={
                            "success": True,
                            "data": {
                                "accessToken": "eyJ...",
                                "refreshToken": "eyJ...",
                                "user": {"id": "google_1029384756", "nickname": "여행자"},
                            },
                            "error": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="소셜 인증 실패 (토큰 검증 실패 또는 이메일 확인 불가)",
                examples=[
                    OpenApiExample(
                        "소셜 인증 실패",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "OAUTH_FAILED",
                                "message": "소셜 인증에 실패했습니다.",
                            },
                        },
                        response_only=True,
                    )
                ],
            ),
            409: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="동일한 이메일로 가입된 계정이 이미 존재함",
                examples=[
                    OpenApiExample(
                        "이메일 충돌",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "SOCIAL_EMAIL_CONFLICT",
                                "message": "이미 가입된 이메일과 연결된 계정입니다.",
                            },
                        },
                        response_only=True,
                    )
                ],
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="provider 또는 oauthToken 필드 누락 또는 형식 검증 실패",
            ),
        },
        examples=[
            OpenApiExample(
                "소셜 로그인 요청",
                value={"provider": "google", "oauthToken": "eyJ..."},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        oauth_token = serializer.validated_data["oauthToken"]

        if provider == User.Provider.GOOGLE:
            profile = verify_google_id_token(oauth_token)
        else:
            profile = verify_kakao_token(oauth_token)

        user = find_or_create_social_user(
            provider=provider,
            provider_id=profile["provider_id"],
            email=profile["email"],
            nickname=profile["nickname"],
        )

        refresh = RefreshToken.for_user(user)
        return ApiResponse(
            data={
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
                "user": {
                    "id": user.username,
                    "nickname": user.nickname,
                },
            }
        )


class SendEmailVerificationCodeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="이메일 인증번호 발송",
        description=(
            "이메일 인증 목적에 맞는 6자리 인증번호를 발급해 이메일로 전송합니다. "
            "같은 이메일과 인증 목적으로 다시 요청하면 이전 미사용 인증번호는 "
            "무효화됩니다."
        ),
        tags=["Auth"],
        auth=[],
        request=SendEmailVerificationCodeSerializer,
        responses={
            200: OpenApiResponse(
                response=SendEmailVerificationCodeSuccessResponseSerializer,
                description="인증번호 발송 성공",
                examples=[
                    OpenApiExample(
                        "발송 성공",
                        value={
                            "success": True,
                            "data": {"message": "인증번호가 발송되었습니다."},
                            "error": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="이메일 형식 또는 인증 목적 검증 실패",
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="인증번호 저장 또는 이메일 발송 실패",
            ),
        },
        examples=[
            OpenApiExample(
                "회원가입 인증번호 요청",
                value={
                    "email": "traveler@example.com",
                    "purpose": "signup",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = SendEmailVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_email_verification_code(**serializer.validated_data)
        return ApiResponse(data={"message": "인증번호가 발송되었습니다."})


class VerifyEmailVerificationCodeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="이메일 인증번호 확인",
        description=(
            "이메일과 인증 목적에 맞는 6자리 인증번호가 유효한지 확인합니다. "
            "확인만으로 인증번호를 소비하지 않으며, 회원가입이 성공할 때 최종 "
            "사용 처리됩니다."
        ),
        tags=["Auth"],
        auth=[],
        request=VerifyEmailVerificationCodeSerializer,
        responses={
            200: OpenApiResponse(
                response=VerifyEmailVerificationCodeSuccessResponseSerializer,
                description="인증번호 확인 성공",
                examples=[
                    OpenApiExample(
                        "확인 성공",
                        value={
                            "success": True,
                            "data": {"message": "인증번호가 확인되었습니다."},
                            "error": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="인증번호 불일치, 만료 또는 이미 사용됨",
                examples=[
                    OpenApiExample(
                        "인증번호 불일치",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "CODE_MISMATCH",
                                "message": "인증번호가 일치하지 않습니다.",
                            },
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "인증번호 만료",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "CODE_EXPIRED",
                                "message": "인증번호가 만료되었습니다.",
                            },
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "이미 사용된 인증번호",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "CODE_ALREADY_USED",
                                "message": "이미 사용된 인증번호입니다.",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="이메일, 인증번호 형식 또는 인증 목적 검증 실패",
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="서버 내부 오류",
            ),
        },
        examples=[
            OpenApiExample(
                "회원가입 인증번호 확인",
                value={
                    "email": "traveler@example.com",
                    "code": "123456",
                    "purpose": "signup",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = VerifyEmailVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verify_email_verification_code(**serializer.validated_data)
        return ApiResponse(data={"message": "인증번호가 확인되었습니다."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="비밀번호 재설정 인증번호 발송",
        description=(
            "가입 여부를 노출하지 않도록 이메일 존재 여부와 무관하게 동일한 성공 "
            "응답을 반환하며, 가입된 이메일에만 인증번호를 발송합니다."
        ),
        tags=["Auth"],
        auth=[],
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=PasswordResetRequestSuccessResponseSerializer,
                description="비밀번호 재설정 인증번호 발송 요청 성공",
                examples=[
                    OpenApiExample(
                        "발송 요청 성공",
                        value={
                            "success": True,
                            "data": {"message": "인증번호가 발송되었습니다."},
                            "error": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="이메일 필드 누락 또는 형식 검증 실패",
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="인증번호 저장 또는 이메일 발송 실패",
            ),
        },
        examples=[
            OpenApiExample(
                "비밀번호 재설정 인증번호 요청",
                value={"email": "traveler@example.com"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_password_reset_code(email=serializer.validated_data["email"])
        return ApiResponse(data={"message": "인증번호가 발송되었습니다."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="비밀번호 재설정 확인",
        description=(
            "이메일 인증번호와 새 비밀번호를 검증한 뒤 인증번호를 소비하고 "
            "사용자의 비밀번호를 변경합니다."
        ),
        tags=["Auth"],
        auth=[],
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                response=PasswordResetConfirmSuccessResponseSerializer,
                description="비밀번호 재설정 성공",
                examples=[
                    OpenApiExample(
                        "비밀번호 재설정 성공",
                        value={
                            "success": True,
                            "data": {"success": True},
                            "error": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="인증번호 불일치, 만료 또는 이미 사용됨",
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="필드 형식 또는 새 비밀번호 정책 검증 실패",
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="서버 내부 오류",
            ),
        },
        examples=[
            OpenApiExample(
                "비밀번호 재설정 요청",
                value={
                    "email": "traveler@example.com",
                    "code": "123456",
                    "newPw": "new-safe-password-123",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
            new_password=serializer.validated_data["newPw"],
        )
        return ApiResponse(data={"success": True})


class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="회원가입",
        description=(
            "아이디, 비밀번호, 닉네임, 이메일과 발급받은 이메일 인증번호를 받아 "
            "사용자를 생성합니다. 아이디와 이메일은 중복될 수 없으며, 비밀번호는 "
            "서버의 Django 비밀번호 정책을 통과해야 합니다. 가입 성공 시 사용자 "
            "아이디와 JWT 액세스 토큰을 반환합니다."
        ),
        tags=["Auth"],
        auth=[],
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(
                response=SignupSuccessResponseSerializer,
                description="회원가입 성공",
                examples=[
                    OpenApiExample(
                        "회원가입 성공",
                        value={
                            "success": True,
                            "data": {
                                "userId": "traveler",
                                "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                            },
                            "error": None,
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="인증코드, 비밀번호 확인 또는 약관 동의 검증 실패",
                examples=[
                    OpenApiExample(
                        "비밀번호 확인 불일치",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "PASSWORD_MISMATCH",
                                "message": "비밀번호가 일치하지 않습니다.",
                            },
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "인증코드 불일치",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "CODE_MISMATCH",
                                "message": "인증번호가 일치하지 않습니다.",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            409: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="아이디 또는 이메일 중복",
                examples=[
                    OpenApiExample(
                        "아이디 중복",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "DUPLICATE_ID",
                                "message": "이미 사용 중인 아이디입니다.",
                            },
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "이메일 중복",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "DUPLICATE_EMAIL",
                                "message": "이미 사용 중인 이메일입니다.",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="필수 필드, 형식, 길이 또는 비밀번호 강도 검증 실패",
                examples=[
                    OpenApiExample(
                        "필드 검증 실패",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "COMMON_422",
                                "message": "요청 값이 올바르지 않습니다.",
                                "details": {
                                    "email": ["유효한 이메일 주소를 입력하십시오."]
                                },
                            },
                        },
                        response_only=True,
                    )
                ],
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="서버 내부 오류",
            ),
        },
        examples=[
            OpenApiExample(
                "회원가입 요청",
                value={
                    "id": "traveler",
                    "pw": "safe-password-123",
                    "pwCheck": "safe-password-123",
                    "nickname": "여행자",
                    "email": "traveler@example.com",
                    "verifyCode": "123456",
                    "agreeTerms": True,
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return ApiResponse(
            data={
                "userId": user.username,
                "accessToken": str(refresh.access_token),
            },
            status=201,
        )


class CheckIdView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="아이디 중복 확인",
        description=(
            "회원가입 전에 로그인 아이디의 사용 가능 여부를 확인합니다. "
            "id는 필수이며 공백일 수 없고 최대 150자입니다."
        ),
        tags=["Auth"],
        auth=[],
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="중복 여부를 확인할 로그인 아이디",
                examples=[
                    OpenApiExample("아이디 예시", value="traveler"),
                ],
            )
        ],
        responses={
            200: OpenApiResponse(
                response=CheckIdSuccessResponseSerializer,
                description="아이디 사용 가능 여부 조회 성공",
                examples=[
                    OpenApiExample(
                        "사용 가능한 아이디",
                        value={
                            "success": True,
                            "data": {"available": True},
                            "error": None,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "이미 사용 중인 아이디",
                        value={
                            "success": True,
                            "data": {"available": False},
                            "error": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="id 쿼리 파라미터 누락 또는 형식 검증 실패",
                examples=[
                    OpenApiExample(
                        "아이디 파라미터 누락",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "COMMON_422",
                                "message": "요청 값이 올바르지 않습니다.",
                                "details": {"id": ["이 필드는 필수 항목입니다."]},
                            },
                        },
                        response_only=True,
                    )
                ],
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="서버 내부 오류",
            ),
        },
    )
    def get(self, request):
        serializer = CheckIdSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["id"]
        available = not User.objects.filter(username=user_id).exists()
        return ApiResponse(data={"available": available})
