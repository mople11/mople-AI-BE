from django.urls import path

from accounts.views import (
    CheckIdView,
    LoginView,
    LogoutView,
    SendEmailVerificationCodeView,
    SignupView,
    VerifyEmailVerificationCodeView,
)


app_name = "accounts"

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
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
