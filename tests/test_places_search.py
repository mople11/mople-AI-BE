from decimal import Decimal
from unittest.mock import patch

import pytest

from common.pagination import paginate_queryset
from places.models import TouristSpot
from places.tourapi import RawSpot, TourApiError


def raw_spot(content_id="100", name="순천만", category="ATTRACTION"):
    return RawSpot(content_id=content_id, name=name, category=category, address="전라남도 순천시", latitude=Decimal("34.885"), longitude=Decimal("127.509"), image_urls=[f"https://example.com/{content_id}.jpg"])


def test_paginate_queryset_rejects_non_positive_page_size():
    with pytest.raises(ValueError, match="page_size는 1 이상"):
        paginate_queryset([], page=1, page_size=0)


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
    assert response.data["data"]["pagination"] == {
        "page": 1, "pageSize": 20, "totalCount": 2, "totalPages": 1,
    }
    assert TouristSpot.objects.count() == 2
    assert mock_search.call_args.kwargs["category"] == "관광지"


@pytest.mark.django_db
@patch("places.services.TourApiClient.search_spots", return_value=[])
def test_search_empty(mock_search, api_client):
    response = api_client.get("/api/v1/search")
    assert response.status_code == 200
    assert response.data["data"] == {
        "results": [],
        "pagination": {"page": 1, "pageSize": 20, "totalCount": 0, "totalPages": 0},
    }


@pytest.mark.django_db
@patch("places.services.TourApiClient.search_spots")
def test_search_paginates_and_returns_empty_for_page_past_end(mock_search, api_client):
    mock_search.return_value = [raw_spot(str(index), f"장소 {index}") for index in range(3)]

    second = api_client.get("/api/v1/search", {"page": 2, "pageSize": 2})
    past_end = api_client.get("/api/v1/search", {"page": 3, "pageSize": 2})

    assert [item["name"] for item in second.data["data"]["results"]] == ["장소 2"]
    assert second.data["data"]["pagination"] == {
        "page": 2, "pageSize": 2, "totalCount": 3, "totalPages": 2,
    }
    assert past_end.data["data"]["results"] == []
    assert past_end.data["data"]["pagination"]["totalPages"] == 2


@pytest.mark.django_db
@pytest.mark.parametrize("params", [{"page": 0}, {"pageSize": 51}])
def test_search_rejects_invalid_pagination(api_client, params):
    response = api_client.get("/api/v1/search", params)

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


@pytest.mark.django_db
@patch("places.services.TourApiClient.search_spots")
def test_search_accepts_max_page_size(mock_search, api_client):
    mock_search.return_value = [raw_spot("1", "장소 1")]

    response = api_client.get("/api/v1/search", {"pageSize": 50})

    assert response.status_code == 200
    assert response.data["data"]["pagination"]["pageSize"] == 50


@pytest.mark.django_db
@patch("places.services.TourApiClient.search_spots", side_effect=TourApiError())
def test_search_external_failure(mock_search, api_client):
    response = api_client.get("/api/v1/search")
    assert response.status_code == 502
    assert response.data["error"]["code"] == "EXTERNAL_API_ERROR"
