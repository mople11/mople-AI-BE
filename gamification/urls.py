from django.urls import path

from gamification.views import (
    CompletionCardCreateView,
    CompletionCardListView,
    CompletionCardShareView,
    HiddenCourseUnlockedView,
    StampCheckinView,
    StampbookView,
)


app_name = "gamification"

urlpatterns = [
    path("api/v1/stamps/checkin", StampCheckinView.as_view(), name="stamps-checkin"),
    path("api/v1/stamps", StampbookView.as_view(), name="stamps-status"),
    path(
        "api/v1/courses/unlocked",
        HiddenCourseUnlockedView.as_view(),
        name="courses-unlocked",
    ),
    path(
        "api/v1/cards/completion",
        CompletionCardCreateView.as_view(),
        name="cards-completion",
    ),
    path("api/v1/cards", CompletionCardListView.as_view(), name="cards-list"),
    path(
        "api/v1/cards/<int:cardId>/share",
        CompletionCardShareView.as_view(),
        name="cards-share",
    ),
]
