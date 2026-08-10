from django.urls import path

from common.views import UserSettingsView

app_name = "common"

urlpatterns = [
    path("api/v1/settings", UserSettingsView.as_view(), name="settings"),
]
