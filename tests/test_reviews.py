from decimal import Decimal

import pytest
from django.utils import timezone

from accounts.models import User
from places.models import TouristSpot
from reviews.models import Review, ReviewPhoto, ReviewReaction, ReviewReport


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="reviewer", email="reviewer@example.com",
        nickname="여행자", password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def spot():
    return TouristSpot.objects.create(
        content_id="review-spot", name="후기 장소",
        category=TouristSpot.Category.ATTRACTION, address="전라남도 여수시",
        description="후기 테스트 장소", latitude=Decimal("34.7600000"),
        longitude=Decimal("127.6600000"), synced_at=timezone.now(),
    )


@pytest.fixture
def review(user, spot):
    return Review.objects.create(
        user=user, place=spot, rating=4, content="좋아요", weather_at_visit="맑음"
    )


def test_create_review_success(authenticated_client, spot):
    response = authenticated_client.post("/api/v1/reviews", {
        "targetId": str(spot.id), "rating": 5, "text": "멋진 장소예요",
        "photos": ["https://example.com/second.jpg", "https://example.com/first.jpg"],
        "visitDate": "2026-08-01", "visitWeather": "맑음",
    }, format="json")

    assert response.status_code == 200
    assert isinstance(response.data["data"]["reviewId"], str)
    created = Review.objects.get(pk=response.data["data"]["reviewId"])
    assert created.place == spot
    assert created.course is None
    assert list(created.photos.values_list("display_order", flat=True)) == [0, 1]


def test_create_review_requires_rating(authenticated_client, spot):
    response = authenticated_client.post(
        "/api/v1/reviews", {"targetId": spot.id, "text": "별점 없음"}, format="json"
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "RATING_REQUIRED"


def test_create_review_rejects_null_rating_with_rating_required(
    authenticated_client, spot
):
    response = authenticated_client.post(
        "/api/v1/reviews",
        {"targetId": spot.id, "rating": None, "text": "별점 없음"},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "RATING_REQUIRED"


def test_create_review_place_not_found(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/reviews", {"targetId": "999999", "rating": 5, "text": "없음"}, format="json"
    )
    assert response.status_code == 404
    assert response.data["error"]["code"] == "PLACE_NOT_FOUND"


def test_list_reviews_latest_without_authentication(api_client, user, spot):
    first = Review.objects.create(user=user, place=spot, rating=5, content="먼저")
    second = Review.objects.create(user=user, place=spot, rating=2, content="나중")
    ReviewPhoto.objects.create(review=second, image_url="https://example.com/photo.jpg")

    response = api_client.get("/api/v1/reviews", {"targetId": spot.id})

    assert response.status_code == 200
    assert [item["reviewId"] for item in response.data["data"]["reviews"]] == [str(second.id), str(first.id)]
    assert response.data["data"]["reviews"][0]["author"] == "여행자"
    assert response.data["data"]["reviews"][0]["photos"] == ["https://example.com/photo.jpg"]


def test_list_reviews_by_rating(api_client, user, spot):
    low = Review.objects.create(user=user, place=spot, rating=2, content="낮음")
    high = Review.objects.create(user=user, place=spot, rating=5, content="높음")

    response = api_client.get("/api/v1/reviews", {"targetId": spot.id, "sort": "rating"})

    assert response.status_code == 200
    assert [item["reviewId"] for item in response.data["data"]["reviews"]] == [str(high.id), str(low.id)]


def test_list_reviews_rejects_non_numeric_target_id(api_client):
    response = api_client.get("/api/v1/reviews", {"targetId": "not-a-number"})

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_toggle_review_helpful(authenticated_client, user, review):
    url = f"/api/v1/reviews/{review.id}/helpful"
    first = authenticated_client.post(url)
    second = authenticated_client.post(url)

    assert first.data["data"] == {"count": 1}
    assert second.data["data"] == {"count": 0}
    assert not ReviewReaction.objects.filter(review=review, user=user).exists()


def test_helpful_review_not_found(authenticated_client):
    response = authenticated_client.post("/api/v1/reviews/999999/helpful")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "REVIEW_NOT_FOUND"


def test_report_is_idempotent(authenticated_client, user, review):
    url = f"/api/v1/reviews/{review.id}/report"
    first = authenticated_client.post(url, {"reason": "부적절"}, format="json")
    second = authenticated_client.post(url, {"reason": "다른 이유"}, format="json")

    assert first.data["data"] == {"reported": True}
    assert second.data["data"] == {"reported": True}
    assert ReviewReport.objects.filter(review=review, user=user).count() == 1


def test_report_review_not_found(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/reviews/999999/report", {"reason": "없음"}, format="json"
    )
    assert response.status_code == 404
    assert response.data["error"]["code"] == "REVIEW_NOT_FOUND"
