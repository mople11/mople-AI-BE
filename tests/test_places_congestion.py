from unittest.mock import patch

import pytest
from django.utils import timezone

from places.models import TouristSpot
from places.sk_congestion import CongestionData


def create_spot(**overrides):
    values = {
        "content_id": "100", "name": "기존 장소", "category": "ATTRACTION",
        "address": "전라남도 순천시", "description": "", "latitude": 34.885,
        "longitude": 127.509, "synced_at": timezone.now(),
    }
    values.update(overrides)
    return TouristSpot.objects.create(**values)


@pytest.mark.django_db
def test_congestion_missing_spot(api_client):
    response = api_client.get("/api/v1/places/999999/congestion")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "PLACE_NOT_FOUND"


@pytest.mark.django_db
@patch("places.services.SkCongestionClient.get_congestion", return_value=None)
def test_congestion_unavailable_returns_empty_data(mock_congestion, api_client):
    spot = create_spot()
    response = api_client.get(f"/api/v1/places/{spot.id}/congestion")
    assert response.status_code == 200
    assert response.data == {"success": True, "data": {}, "error": None}


@pytest.mark.django_db
@patch("places.services.SkCongestionClient.get_congestion")
def test_congestion_uses_local_parking_value(mock_congestion, api_client):
    spot = create_spot(parking_available=True)
    mock_congestion.return_value = CongestionData(level="여유", hourly_graph=[{"hour": 0, "level": "여유"}], recommended_time="오전 9시")
    response = api_client.get(f"/api/v1/places/{spot.id}/congestion")
    assert response.status_code == 200
    assert response.data["data"] == {"level": "여유", "parkingAvailable": True, "hourlyGraph": [{"hour": 0, "level": "여유"}], "recommendedTime": "오전 9시"}
