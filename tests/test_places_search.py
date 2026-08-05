from decimal import Decimal
from unittest.mock import patch

import pytest

from places.models import TouristSpot
from places.tourapi import RawSpot, TourApiError


def raw_spot(content_id="100", name="순천만", category="ATTRACTION"):
    return RawSpot(content_id=content_id, name=name, category=category, address="전라남도 순천시", latitude=Decimal("34.885"), longitude=Decimal("127.509"), image_urls=[f"https://example.com/{content_id}.jpg"])


@pytest.mark.django_db
@patch("places.services.TourApiClient.search_spots")
def test_search_success(mock_search, api_client):
    mock_search.return_value = [raw_spot(), raw_spot("101", "여수 맛집", "RESTAURANT")]
    response = api_client.get("/api/v1/search", {"category": "관광지", "region": "순천시"})
    assert response.status_code == 200
    assert response.data["error"] is None
    results = response.data["data"]["results"]
    assert len(results) == 2
    assert set(results[0]) == {"id", "name", "category", "location", "rating", "thumbnail"}
    assert results[0]["category"] == "관광지"
    assert results[0]["rating"] == 0
    assert TouristSpot.objects.count() == 2
    assert mock_search.call_args.kwargs["category"] == "관광지"


@pytest.mark.django_db
@patch("places.services.TourApiClient.search_spots", return_value=[])
def test_search_empty(mock_search, api_client):
    response = api_client.get("/api/v1/search")
    assert response.status_code == 200
    assert response.data["data"] == {"results": []}


@pytest.mark.django_db
@patch("places.services.TourApiClient.search_spots", side_effect=TourApiError())
def test_search_external_failure(mock_search, api_client):
    response = api_client.get("/api/v1/search")
    assert response.status_code == 502
    assert response.data["error"]["code"] == "EXTERNAL_API_ERROR"

