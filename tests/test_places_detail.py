from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from accounts.models import User
from places.models import TouristSpot
from places.tourapi import RawSpot, TourApiClient
from reviews.models import Review


def create_spot(**overrides):
    values = {"content_id": "100", "name": "기존 장소", "category": "ATTRACTION", "address": "전라남도 순천시", "description": "", "latitude": Decimal("34.885"), "longitude": Decimal("127.509"), "synced_at": timezone.now()}
    values.update(overrides)
    return TouristSpot.objects.create(**values)


def detail_raw():
    return RawSpot(content_id="100", name="순천만 국가정원", category="ATTRACTION", address="전라남도 순천시", description="설명", hours="09:00~18:00", latitude=Decimal("34.885"), longitude=Decimal("127.509"), parking_available=True, image_urls=["https://example.com/1.jpg"])


def create_reviews(*, spot, ratings):
    user = User.objects.create_user(
        username=f"detail-reviewer-{spot.id}",
        email=f"detail-reviewer-{spot.id}@example.com",
        nickname=f"상세 리뷰어 {spot.id}",
        password="safe-password-123",
    )
    return Review.objects.bulk_create([
        Review(user=user, place=spot, rating=rating, content=f"평점 {rating}")
        for rating in ratings
    ])


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
@patch("places.services.TourApiClient.get_spot_detail", return_value=detail_raw())
def test_detail_returns_average_and_null_summary_below_minimum(mock_detail, api_client):
    spot = create_spot()
    create_reviews(spot=spot, ratings=(3, 4, 5))

    response = api_client.get(f"/api/v1/places/{spot.id}")

    assert response.status_code == 200
    assert response.data["data"]["reviewSummary"] == {
        "avgRating": 4.0,
        "aiSatisfaction": None,
    }


@pytest.mark.django_db
@patch("places.services.get_review_summary")
@patch("places.services.TourApiClient.get_spot_detail", return_value=detail_raw())
def test_detail_reuses_review_summary_result(mock_detail, mock_summary, api_client):
    spot = create_spot()
    create_reviews(spot=spot, ratings=(3, 4, 4, 5, 5))
    mock_summary.return_value = {
        "score": 86,
        "keywords": {"positive": ["경치"], "negative": ["혼잡"]},
    }

    response = api_client.get(f"/api/v1/places/{spot.id}")

    assert response.status_code == 200
    assert response.data["data"]["reviewSummary"] == {
        "avgRating": 4.2,
        "aiSatisfaction": mock_summary.return_value,
    }
    mock_summary.assert_called_once_with(target_id=spot.id)


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


def test_tourapi_detail_common_uses_current_parameters():
    common_item = {
        "contentid": "100",
        "contenttypeid": "12",
        "title": "순천만 국가정원",
        "addr1": "전라남도 순천시",
        "mapy": "34.885",
        "mapx": "127.509",
    }
    client = TourApiClient()

    with patch.object(
        client,
        "_get_items",
        side_effect=[[common_item], [], []],
    ) as get_items:
        client.get_spot_detail(content_id="100")

    endpoint, params = get_items.call_args_list[0].args
    assert endpoint == "detailCommon2"
    assert params["contentId"] == "100"
    assert not {
        "defaultYN",
        "firstImageYN",
        "areacodeYN",
        "catcodeYN",
        "addrinfoYN",
        "mapinfoYN",
        "overviewYN",
    } & params.keys()

    image_endpoint, image_params = get_items.call_args_list[2].args
    assert image_endpoint == "detailImage2"
    assert image_params["contentId"] == "100"
    assert "subImageYN" not in image_params
