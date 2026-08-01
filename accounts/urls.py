from django.urls import path

from accounts.views import (
    CheckIdView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SendEmailVerificationCodeView,
    SignupView,
    SocialLoginView,
    VerifyEmailVerificationCodeView,
)


app_name = "accounts"

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("login/social", SocialLoginView.as_view(), name="login-social"),
    path("logout", LogoutView.as_view(), name="logout"),
    path(
        "password/reset-request",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset-confirm",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "email/verify-code",
        SendEmailVerificationCodeView.as_view(),
        name="send-email-verification-code",
    ),
    path(
        "email/verify-confirm",
        VerifyEmailVerificationCodeView.as_view(),
        name="verify-email-verification-code",
    ),
    path("signup", SignupView.as_view(), name="signup"),
    path("signup/check-id", CheckIdView.as_view(), name="check-id"),
]
