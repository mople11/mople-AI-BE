from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.openapi import (
    CheckIdSuccessResponseSerializer,
    ErrorResponseSerializer,
    SendEmailVerificationCodeSuccessResponseSerializer,
    SignupSuccessResponseSerializer,
    VerifyEmailVerificationCodeSuccessResponseSerializer,
)
from accounts.serializers import (
    CheckIdSerializer,
    SendEmailVerificationCodeSerializer,
    SignupSerializer,
    VerifyEmailVerificationCodeSerializer,
)
from accounts.services import (
    send_email_verification_code,
    verify_email_verification_code,
)
from common.response import ApiResponse


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
