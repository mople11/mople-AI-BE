from django.urls import path

from gamification.views import StampCheckinView, StampbookView


app_name = "gamification"

urlpatterns = [
    path("api/v1/stamps/checkin", StampCheckinView.as_view(), name="stamps-checkin"),
    path("api/v1/stamps", StampbookView.as_view(), name="stamps-status"),
]
