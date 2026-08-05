from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from places.models import TouristSpot
from places.tourapi import RawSpot


def create_spot(**overrides):
    values = {"content_id": "100", "name": "기존 장소", "category": "ATTRACTION", "address": "전라남도 순천시", "description": "", "latitude": Decimal("34.885"), "longitude": Decimal("127.509"), "synced_at": timezone.now()}
    values.update(overrides)
    return TouristSpot.objects.create(**values)


def detail_raw():
    return RawSpot(content_id="100", name="순천만 국가정원", category="ATTRACTION", address="전라남도 순천시", description="설명", hours="09:00~18:00", latitude=Decimal("34.885"), longitude=Decimal("127.509"), parking_available=True, image_urls=["https://example.com/1.jpg"])


@pytest.mark.django_db
@patch("places.services.TourApiClient.get_spot_detail", return_value=detail_raw())
def test_detail_success_with_distance(mock_detail, api_client):
    spot = create_spot()
    response = api_client.get(f"/api/v1/places/{spot.id}", {"latitude": "34.8", "longitude": "127.4"})
    assert response.status_code == 200
    data = response.data["data"]
    assert data["map"] == {"lat": 34.885, "lng": 127.509}
    assert data["distanceFromUser"] == "13.7km"
    assert data["reviewSummary"] == {"avgRating": 0, "aiSatisfaction": None}
    assert data["category"] == "관광지"


@pytest.mark.django_db
@patch("places.services.TourApiClient.get_spot_detail", return_value=detail_raw())
def test_detail_without_location_has_null_distance(mock_detail, api_client):
    spot = create_spot()
    response = api_client.get(f"/api/v1/places/{spot.id}")
    assert response.data["data"]["distanceFromUser"] is None


@pytest.mark.django_db
def test_detail_missing_local_spot(api_client):
    response = api_client.get("/api/v1/places/999999")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "PLACE_NOT_FOUND"


@pytest.mark.django_db
@patch("places.services.TourApiClient.get_spot_detail", return_value=None)
def test_detail_removed_from_tourapi(mock_detail, api_client):
    spot = create_spot()
    response = api_client.get(f"/api/v1/places/{spot.id}")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "PLACE_NOT_FOUND"

