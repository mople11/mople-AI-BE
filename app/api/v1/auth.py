from fastapi import APIRouter, Depends

from app.core.security import require_auth
from app.schemas.domain.auth import (
    AuthTokenResponse,
    AuthUserResponse,
    EmailSendRequest,
    EmailSendResponse,
    EmailVerifyRequest,
    EmailVerifyResponse,
    IdDuplicateCheckResponse,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetResponse,
    SignupRequest,
    SignupResponse,
    SocialLoginRequest,
)
from app.schemas.response import ApiResponse

router = APIRouter()


@router.post("/signup", response_model=ApiResponse[SignupResponse])
def signup(request: SignupRequest) -> ApiResponse[SignupResponse]:
    return ApiResponse(
        data=SignupResponse(userId="mock-user", accessToken="mock-access-token")
    )


@router.get("/signup/check-id", response_model=ApiResponse[IdDuplicateCheckResponse])
def check_id_duplicate(id: str) -> ApiResponse[IdDuplicateCheckResponse]:
    return ApiResponse(data=IdDuplicateCheckResponse(available=True))


@router.post("/login", response_model=ApiResponse[AuthTokenResponse])
def login(request: LoginRequest) -> ApiResponse[AuthTokenResponse]:
    return ApiResponse(
        data=AuthTokenResponse(
            accessToken="mock-access-token",
            refreshToken="mock-refresh-token",
            user=AuthUserResponse(id="mock-user", nickname="여행자"),
        )
    )


@router.post("/login/social", response_model=ApiResponse[AuthTokenResponse])
def social_login(request: SocialLoginRequest) -> ApiResponse[AuthTokenResponse]:
    return ApiResponse(
        data=AuthTokenResponse(
            accessToken="mock-social-token",
            refreshToken="mock-refresh-token",
            user=AuthUserResponse(id="mock-user", nickname="여행자"),
        )
    )


@router.post("/logout", response_model=ApiResponse[None])
def logout(current_user: dict[str, str] = Depends(require_auth)) -> ApiResponse[None]:
    return ApiResponse(data=None)


@router.post("/email/verify-code", response_model=ApiResponse[EmailSendResponse])
def send_email_code(request: EmailSendRequest) -> ApiResponse[EmailSendResponse]:
    return ApiResponse(data=EmailSendResponse(sent=True))


@router.post("/email/verify-confirm", response_model=ApiResponse[EmailVerifyResponse])
def verify_email_code(request: EmailVerifyRequest) -> ApiResponse[EmailVerifyResponse]:
    return ApiResponse(data=EmailVerifyResponse(verified=True))


@router.post("/password/reset-request", response_model=ApiResponse[EmailSendResponse])
def send_password_reset_code(request: EmailSendRequest) -> ApiResponse[EmailSendResponse]:
    return ApiResponse(data=EmailSendResponse(sent=True))


@router.post("/password/reset-confirm", response_model=ApiResponse[PasswordResetResponse])
def reset_password(
    request: PasswordResetConfirmRequest,
) -> ApiResponse[PasswordResetResponse]:
    return ApiResponse(data=PasswordResetResponse(success=True))
