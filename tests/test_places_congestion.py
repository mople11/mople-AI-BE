from unittest.mock import patch

import pytest
from django.utils import timezone

from places.models import TouristSpot
from places.tourist_congestion import CongestionForecast


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
@patch("places.services.TouristCongestionClient.get_forecast", return_value=None)
def test_congestion_unavailable_returns_empty_data(mock_congestion, api_client):
    spot = create_spot()
    response = api_client.get(f"/api/v1/places/{spot.id}/congestion")
    assert response.status_code == 200
    assert response.data == {"success": True, "data": {}, "error": None}


@pytest.mark.django_db
@patch("places.services.TouristCongestionClient.get_forecast")
def test_congestion_uses_local_parking_value(mock_congestion, api_client):
    spot = create_spot(parking_available=True, sigungu="순천시")
    mock_congestion.return_value = CongestionForecast(
        level="보통",
        concentration_rate=57.2,
        forecast_date="2026-08-05",
        recommended_date="2026-08-10",
    )
    response = api_client.get(f"/api/v1/places/{spot.id}/congestion")
    assert response.status_code == 200
    assert response.data["data"] == {
        "level": "보통",
        "concentrationRate": 57.2,
        "forecastDate": "2026-08-05",
        "parkingAvailable": True,
        "recommendedDate": "2026-08-10",
    }
    mock_congestion.assert_called_once_with(
        spot_name="기존 장소", sigungu="순천시"
    )
