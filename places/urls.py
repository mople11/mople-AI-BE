from django.urls import path

from places.views import (
    SpotCongestionView, SpotDetailView, SpotSearchView, TrafficCongestionView,
)


app_name = "places"

urlpatterns = [
    path("api/v1/search", SpotSearchView.as_view(), name="search"),
    path("api/v1/places/<int:place_id>", SpotDetailView.as_view(), name="detail"),
    path("api/v1/places/<int:place_id>/congestion", SpotCongestionView.as_view(), name="congestion"),
    path("api/v1/traffic/congestion", TrafficCongestionView.as_view(), name="traffic-congestion"),
]

