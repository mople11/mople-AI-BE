from typing import Literal

from pydantic import BaseModel


class SignupRequest(BaseModel):
    id: str
    pw: str
    pwCheck: str
    nickname: str
    email: str
    verifyCode: str
    agreeTerms: bool


class SignupResponse(BaseModel):
    userId: str
    accessToken: str


class LoginRequest(BaseModel):
    id: str
    pw: str


class AuthUserResponse(BaseModel):
    id: str
    nickname: str


class AuthTokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: AuthUserResponse


class IdDuplicateCheckResponse(BaseModel):
    available: bool


class EmailSendRequest(BaseModel):
    email: str


class EmailSendResponse(BaseModel):
    sent: bool


class EmailVerifyRequest(BaseModel):
    email: str
    code: str


class EmailVerifyResponse(BaseModel):
    verified: bool


class PasswordResetConfirmRequest(BaseModel):
    email: str
    code: str
    newPw: str


class PasswordResetResponse(BaseModel):
    success: bool


class SocialLoginRequest(BaseModel):
    provider: Literal["google", "kakao"]
    oauthToken: str
