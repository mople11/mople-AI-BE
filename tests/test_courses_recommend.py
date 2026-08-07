import json
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests
from django.utils import timezone

from accounts.models import User
from courses.ai_recommend import (
    AIRecommendation,
    AIRecommendClient,
    AIRecommendError,
    RecommendedPlace,
)
from courses.models import Course, CoursePlace, CourseProgress
from places.models import TouristSpot


pytestmark = pytest.mark.django_db
RECOMMEND_URL = "/api/v1/recommend/ai"


@pytest.fixture
def user():
    return User.objects.create_user(
        username="ai-traveler",
        email="ai-traveler@example.com",
        nickname="AI 여행자",
        password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def spots():
    return [
        TouristSpot.objects.create(
            content_id=f"recommend-{order}",
            name=f"추천 장소 {order}",
            category=TouristSpot.Category.ATTRACTION,
            address="전라남도 여수시",
            latitude=Decimal(f"34.76{order:02d}00"),
            longitude=Decimal(f"127.66{order:02d}00"),
            synced_at=timezone.now(),
        )
        for order in (1, 2)
    ]


@pytest.fixture
def recommendation(spots):
    return AIRecommendation(
        name="기분 전환 여수 코스",
        reason="바다를 보며 기분을 전환할 수 있어요.",
        places=[
            RecommendedPlace(content_id=spot.content_id, order=order)
            for order, spot in enumerate(spots, start=1)
        ],
    )


def request_payload():
    return {
        "mood": "답답해요",
        "companion": "친구",
        "transport": "자차",
        "timeAvailable": "3시간",
        "freeText": "바다를 보고 싶어요",
    }


def post_recommendation(client, recommendation):
    with patch(
        "courses.services.AIRecommendClient.recommend",
        return_value=recommendation,
    ):
        return client.post(RECOMMEND_URL, request_payload(), format="json")


def test_ai_recommend_success(
    authenticated_client,
    user,
    recommendation,
    spots,
):
    response = post_recommendation(authenticated_client, recommendation)

    assert response.status_code == 200
    course = Course.objects.get(pk=response.data["data"]["courseId"])
    assert response.data == {
        "success": True,
        "data": {
            "courseId": course.id,
            "name": recommendation.name,
            "reason": recommendation.reason,
            "places": [
                {"placeId": spots[0].id, "order": 1},
                {"placeId": spots[1].id, "order": 2},
            ],
        },
        "error": None,
    }
    assert course.status == Course.Status.TEMP
    assert course.owner == user
    assert course.mood == "답답해요"
    assert course.companion_type == "친구"
    assert course.transport_type == "자차"
    assert course.time_available == "3시간"
    assert course.free_text == "바다를 보고 싶어요"
    assert list(
        course.places.order_by("order").values_list("place_id", "order")
    ) == [(spots[0].id, 1), (spots[1].id, 2)]


@pytest.mark.parametrize("mood", [None, "", "   "])
def test_ai_recommend_requires_non_blank_mood(authenticated_client, mood):
    payload = request_payload()
    if mood is None:
        payload.pop("mood")
    else:
        payload["mood"] = mood

    response = authenticated_client.post(RECOMMEND_URL, payload, format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "MOOD_REQUIRED"


def test_ai_recommend_adapter_failure_rolls_back(authenticated_client):
    with patch(
        "courses.services.AIRecommendClient.recommend",
        side_effect=AIRecommendError,
    ):
        response = authenticated_client.post(
            RECOMMEND_URL, request_payload(), format="json"
        )

    assert response.status_code == 500
    assert response.data["error"]["code"] == "AI_RECOMMEND_FAILED"
    assert not Course.objects.exists()


def test_ai_recommend_rejects_empty_places(authenticated_client):
    recommendation = AIRecommendation(name="빈 코스", reason="없음", places=[])
    with patch(
        "courses.services.AIRecommendClient.recommend",
        return_value=recommendation,
    ):
        response = authenticated_client.post(
            RECOMMEND_URL, request_payload(), format="json"
        )

    assert response.status_code == 500
    assert response.data["error"]["code"] == "AI_RECOMMEND_FAILED"
    assert not Course.objects.exists()


def test_ai_recommend_grounding_failure_rolls_back(
    authenticated_client,
    spots,
):
    recommendation = AIRecommendation(
        name="그라운딩 실패 코스",
        reason="로컬에 없는 장소가 포함되어 있어요.",
        places=[
            RecommendedPlace(content_id=spots[0].content_id, order=1),
            RecommendedPlace(content_id="missing-content-id", order=2),
        ],
    )
    with patch(
        "courses.services.AIRecommendClient.recommend",
        return_value=recommendation,
    ):
        response = authenticated_client.post(
            RECOMMEND_URL, request_payload(), format="json"
        )

    assert response.status_code == 500
    assert response.data["error"]["code"] == "AI_RECOMMEND_FAILED"
    assert not Course.objects.exists()
    assert not CoursePlace.objects.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [("companion", "직장동료"), ("transport", "비행기")],
)
def test_ai_recommend_rejects_invalid_choices(
    authenticated_client,
    field,
    value,
):
    payload = request_payload()
    payload[field] = value

    response = authenticated_client.post(RECOMMEND_URL, payload, format="json")

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mood", "기" * 51),
        ("timeAvailable", "시" * 51),
        ("freeText", "여" * 501),
    ],
)
def test_ai_recommend_rejects_overlong_text(
    authenticated_client,
    field,
    value,
):
    payload = request_payload()
    payload[field] = value

    response = authenticated_client.post(RECOMMEND_URL, payload, format="json")

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_ai_recommend_requires_authentication(api_client):
    response = api_client.post(RECOMMEND_URL, request_payload(), format="json")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"


def test_ai_recommended_course_supports_existing_course_flow(
    authenticated_client,
    user,
    recommendation,
    spots,
    settings,
):
    response = post_recommendation(authenticated_client, recommendation)
    course_id = response.data["data"]["courseId"]

    save_response = authenticated_client.post(
        f"/api/v1/courses/{course_id}/save"
    )
    start_response = authenticated_client.post(
        f"/api/v1/courses/{course_id}/start"
    )
    complete_response = authenticated_client.post(
        f"/api/v1/courses/{course_id}/complete",
        {
            "checkInLocations": [
                {"lat": float(spot.latitude), "lng": float(spot.longitude)}
                for spot in spots
            ]
        },
        format="json",
    )
    share_response = authenticated_client.post(
        f"/api/v1/courses/{course_id}/share"
    )

    assert save_response.status_code == 200
    assert start_response.status_code == 200
    assert complete_response.status_code == 200
    assert share_response.status_code == 200
    assert share_response.data["data"]["shareUrl"] == (
        f"{settings.COURSE_SHARE_BASE_URL}/{course_id}"
    )
    assert CourseProgress.objects.get(
        user=user, course_id=course_id
    ).status == CourseProgress.Status.COMPLETED


def test_ai_client_calls_llm_with_search_candidates(settings, spots):
    settings.LLM_API_BASE_URL = "https://llm.example/v1"
    settings.LLM_API_KEY = "test-key"
    settings.LLM_API_MODEL = "test-model"
    settings.LLM_API_TIMEOUT_SEC = 7
    llm_response = Mock()
    llm_response.raise_for_status.return_value = None
    llm_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "name": "테스트 코스",
                            "reason": "테스트 이유",
                            "places": [
                                {"content_id": spots[1].content_id},
                                {"content_id": spots[0].content_id},
                            ],
                        }
                    )
                }
            }
        ]
    }

    with (
        patch.object(AIRecommendClient, "_get_candidates", return_value=spots),
        patch("courses.ai_recommend.requests.post", return_value=llm_response) as post,
    ):
        result = AIRecommendClient().recommend(
            mood="신나요",
            companion="친구",
            transport="자차",
            time_available="3시간",
            free_text="바다",
        )

    assert [(place.content_id, place.order) for place in result.places] == [
        (spots[1].content_id, 1),
        (spots[0].content_id, 2),
    ]
    assert post.call_args.kwargs["timeout"] == 7
    assert post.call_args.kwargs["json"]["model"] == "test-model"


def test_ai_client_falls_back_to_all_candidates_when_keyword_has_no_results(
    spots,
):
    with patch(
        "courses.ai_recommend.search_spots",
        side_effect=[[], spots],
    ) as search:
        candidates = AIRecommendClient()._get_candidates(
            free_text="바다를 보고 싶어요"
        )

    assert candidates == spots
    assert [call.kwargs["keyword"] for call in search.call_args_list] == [
        "바다를 보고 싶어요",
        None,
    ]


def test_ai_client_does_not_use_mood_when_free_text_is_empty(spots):
    with patch(
        "courses.ai_recommend.search_spots",
        return_value=spots,
    ) as search:
        candidates = AIRecommendClient()._get_candidates(free_text="")

    assert candidates == spots
    assert search.call_count == 1
    assert search.call_args.kwargs["keyword"] is None


def test_ai_recommend_returns_failure_when_candidate_fallback_is_empty(
    authenticated_client,
):
    with patch(
        "courses.ai_recommend.search_spots",
        side_effect=[[], []],
    ) as search:
        response = authenticated_client.post(
            RECOMMEND_URL, request_payload(), format="json"
        )

    assert [call.kwargs["keyword"] for call in search.call_args_list] == [
        request_payload()["freeText"],
        None,
    ]
    assert response.status_code == 500
    assert response.data["error"]["code"] == "AI_RECOMMEND_FAILED"
    assert not Course.objects.exists()


def test_ai_client_converts_request_failure(settings, spots):
    with (
        patch.object(AIRecommendClient, "_get_candidates", return_value=spots),
        patch(
            "courses.ai_recommend.requests.post",
            side_effect=requests.RequestException,
        ),
        pytest.raises(AIRecommendError),
    ):
        AIRecommendClient().recommend(
            mood="신나요",
            companion="",
            transport="",
            time_available="",
            free_text="",
        )
