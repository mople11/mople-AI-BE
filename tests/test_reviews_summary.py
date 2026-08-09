from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from accounts.models import User
from places.models import TouristSpot
from reviews.ai_summary import AISummaryClient, AISummaryError, ReviewSummaryResult
from reviews.models import Review, ReviewSummaryCache


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="summary-reviewer",
        email="summary-reviewer@example.com",
        nickname="요약 여행자",
        password="safe-password-123",
    )


@pytest.fixture
def spot():
    return TouristSpot.objects.create(
        content_id="summary-spot",
        name="요약 장소",
        category=TouristSpot.Category.ATTRACTION,
        address="전라남도 순천시",
        description="리뷰 요약 테스트 장소",
        latitude=Decimal("34.9500000"),
        longitude=Decimal("127.4800000"),
        synced_at=timezone.now(),
    )


def create_reviews(*, user, spot, count):
    return Review.objects.bulk_create([
        Review(user=user, place=spot, rating=4, content=f"후기 {index}")
        for index in range(count)
    ])


@pytest.mark.parametrize("review_count", [0, 4])
@patch("reviews.services.AISummaryClient.summarize")
def test_summary_returns_empty_below_minimum_reviews(
    summarize, api_client, user, spot, review_count
):
    create_reviews(user=user, spot=spot, count=review_count)

    response = api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    assert response.status_code == 200
    assert response.data["data"] == {}
    summarize.assert_not_called()


@patch("reviews.services.AISummaryClient.summarize")
def test_summary_creates_cache_when_reviews_are_sufficient(
    summarize, api_client, user, spot
):
    reviews = create_reviews(user=user, spot=spot, count=5)
    summarize.return_value = ReviewSummaryResult(
        score=86,
        positive=["경치", "친절"],
        negative=["주차"],
    )

    response = api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    assert response.status_code == 200
    assert response.data["data"] == {
        "score": 86,
        "keywords": {"positive": ["경치", "친절"], "negative": ["주차"]},
    }
    summarize.assert_called_once_with(
        reviews=[review.content for review in reversed(reviews)]
    )
    cache = ReviewSummaryCache.objects.get(place=spot)
    assert cache.review_count_at_calc == 5
    assert cache.score == 86


@patch("reviews.services.AISummaryClient.summarize")
def test_summary_sends_only_latest_fifty_review_contents(
    summarize, api_client, user, spot
):
    reviews = create_reviews(user=user, spot=spot, count=55)
    summarize.return_value = ReviewSummaryResult(score=80, positive=[], negative=[])

    api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    summarize.assert_called_once_with(
        reviews=[review.content for review in reversed(reviews[-50:])]
    )


@pytest.mark.parametrize(
    ("positive", "negative"),
    [([1], []), ([], [{"keyword": "혼잡"}])],
)
def test_ai_summary_parser_rejects_non_string_keywords(positive, negative):
    client = AISummaryClient()

    with pytest.raises(ValueError, match="must be strings"):
        client._parse_summary({
            "score": 80,
            "positive": positive,
            "negative": negative,
        })


@patch("reviews.services.AISummaryClient.summarize")
def test_summary_uses_cache_before_recompute_interval(
    summarize, api_client, user, spot
):
    create_reviews(user=user, spot=spot, count=7)
    ReviewSummaryCache.objects.create(
        place=spot,
        score=70,
        positive_keywords=["산책"],
        negative_keywords=["대기"],
        review_count_at_calc=5,
    )

    response = api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    assert response.data["data"] == {
        "score": 70,
        "keywords": {"positive": ["산책"], "negative": ["대기"]},
    }
    summarize.assert_not_called()


@patch("reviews.services.AISummaryClient.summarize")
def test_summary_recomputes_cache_at_interval(summarize, api_client, user, spot):
    create_reviews(user=user, spot=spot, count=10)
    cache = ReviewSummaryCache.objects.create(
        place=spot,
        score=60,
        positive_keywords=["기존 장점"],
        negative_keywords=["기존 단점"],
        review_count_at_calc=5,
    )
    summarize.return_value = ReviewSummaryResult(
        score=91,
        positive=["새 장점"],
        negative=["새 단점"],
    )

    response = api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    assert response.data["data"]["score"] == 91
    summarize.assert_called_once()
    cache.refresh_from_db()
    assert cache.score == 91
    assert cache.positive_keywords == ["새 장점"]
    assert cache.negative_keywords == ["새 단점"]
    assert cache.review_count_at_calc == 10


@patch("reviews.services.AISummaryClient.summarize")
def test_summary_returns_empty_when_llm_fails_without_cache(
    summarize, api_client, user, spot
):
    create_reviews(user=user, spot=spot, count=5)
    summarize.side_effect = AISummaryError("failure")

    response = api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    assert response.status_code == 200
    assert response.data["data"] == {}
    assert not ReviewSummaryCache.objects.filter(place=spot).exists()


@patch("reviews.services.AISummaryClient.summarize")
def test_summary_falls_back_to_cache_when_recompute_fails(
    summarize, api_client, user, spot
):
    create_reviews(user=user, spot=spot, count=10)
    cache = ReviewSummaryCache.objects.create(
        place=spot,
        score=77,
        positive_keywords=["편안함"],
        negative_keywords=["혼잡"],
        review_count_at_calc=5,
    )
    summarize.side_effect = AISummaryError("failure")

    response = api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    assert response.status_code == 200
    assert response.data["data"] == {
        "score": 77,
        "keywords": {"positive": ["편안함"], "negative": ["혼잡"]},
    }
    cache.refresh_from_db()
    assert cache.review_count_at_calc == 5


@patch("reviews.services.AISummaryClient.summarize")
def test_summary_nonexistent_target_returns_empty(summarize, api_client):
    response = api_client.get("/api/v1/reviews/summary", {"targetId": 999999})

    assert response.status_code == 200
    assert response.data["data"] == {}
    summarize.assert_not_called()


def test_summary_allows_unauthenticated_request(api_client, spot):
    response = api_client.get("/api/v1/reviews/summary", {"targetId": spot.id})

    assert response.status_code == 200
