from django.urls import path

from accounts.views import CheckIdView, SignupView


app_name = "accounts"

urlpatterns = [
    path("signup", SignupView.as_view(), name="signup"),
    path("signup/check-id", CheckIdView.as_view(), name="check-id"),
]
