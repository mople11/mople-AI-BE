from django.urls import path

from interactions.views import BookmarkToggleView


app_name = "interactions"

urlpatterns = [
    path(
        "api/v1/places/<int:placeId>/like",
        BookmarkToggleView.as_view(),
        name="bookmark-toggle",
    ),
]
