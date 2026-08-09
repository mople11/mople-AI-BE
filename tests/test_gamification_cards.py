from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from accounts.models import User
from courses.models import Course, CourseProgress
from gamification.models import (
    CompletionCard,
    HiddenCourse,
    UserHiddenCourseUnlock,
)


pytestmark = pytest.mark.django_db

UNLOCKED_URL = "/api/v1/courses/unlocked"
COMPLETION_URL = "/api/v1/cards/completion"
CARDS_URL = "/api/v1/cards"


@pytest.fixture
def user():
    return User.objects.create_user(
        username="card-collector",
        email="card-collector@example.com",
        nickname="카드 수집가",
        password="safe-password-123",
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        username="other-card-collector",
        email="other-card-collector@example.com",
        nickname="다른 카드 수집가",
        password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def course():
    return Course.objects.create(name="여수 밤바다 코스")


def test_hidden_courses_are_split_by_unlock_status(authenticated_client, user):
    unlocked_course = Course.objects.create(name="해금 코스")
    locked_course = Course.objects.create(name="잠긴 코스")
    unlocked_hidden_course = HiddenCourse.objects.create(
        course=unlocked_course,
        rarity=HiddenCourse.Rarity.RARE,
        unlock_condition="맑은 날 방문",
    )
    HiddenCourse.objects.create(
        course=locked_course,
        rarity=HiddenCourse.Rarity.COMMON,
        unlock_condition="비 오는 날 방문",
    )
    UserHiddenCourseUnlock.objects.create(
        user=user, hidden_course=unlocked_hidden_course
    )

    response = authenticated_client.get(
        UNLOCKED_URL, {"lat": 34.76, "lng": 127.66}
    )

    assert response.status_code == 200
    assert response.data["data"] == {
        "unlockedCourses": [
            {"courseId": unlocked_course.id, "rarity": "RARE"}
        ],
        "lockedCourses": [
            {
                "courseId": locked_course.id,
                "unlockCondition": "비 오는 날 방문",
            }
        ],
    }


def test_hidden_courses_requires_coordinates(authenticated_client):
    response = authenticated_client.get(UNLOCKED_URL)

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_hidden_courses_requires_authentication(api_client):
    response = api_client.get(UNLOCKED_URL, {"lat": 34.76, "lng": 127.66})

    assert response.status_code == 401


def test_create_completion_card_success(authenticated_client, user, course):
    CourseProgress.objects.create(
        user=user, course=course, status=CourseProgress.Status.COMPLETED
    )
    user_photo = "https://example.com/completed.jpg"

    response = authenticated_client.post(
        COMPLETION_URL,
        {"courseId": course.id, "userPhoto": user_photo},
        format="json",
    )

    assert response.status_code == 200
    card = CompletionCard.objects.get(user=user, course=course)
    assert response.data["data"] == {
        "cardId": card.id,
        "cardImageUrl": user_photo,
    }
    assert card.user_photo == user_photo
    assert card.card_image_url == user_photo


def test_create_completion_card_rejects_invalid_user_photo(
    authenticated_client, course
):
    response = authenticated_client.post(
        COMPLETION_URL,
        {"courseId": course.id, "userPhoto": "not-a-url"},
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_create_completion_card_requires_authentication(api_client, course):
    response = api_client.post(
        COMPLETION_URL,
        {
            "courseId": course.id,
            "userPhoto": "https://example.com/completed.jpg",
        },
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "progress_status",
    [None, CourseProgress.Status.SAVED, CourseProgress.Status.IN_PROGRESS],
)
def test_create_completion_card_rejects_uncompleted_course(
    authenticated_client, user, course, progress_status
):
    if progress_status:
        CourseProgress.objects.create(
            user=user, course=course, status=progress_status
        )

    response = authenticated_client.post(
        COMPLETION_URL,
        {
            "courseId": course.id,
            "userPhoto": "https://example.com/not-completed.jpg",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "COURSE_NOT_COMPLETED"
    assert not CompletionCard.objects.filter(user=user, course=course).exists()


def test_create_completion_card_upserts_existing_card(
    authenticated_client, user, course
):
    CourseProgress.objects.create(
        user=user, course=course, status=CourseProgress.Status.COMPLETED
    )
    first_response = authenticated_client.post(
        COMPLETION_URL,
        {
            "courseId": course.id,
            "userPhoto": "https://example.com/first.jpg",
        },
        format="json",
    )
    second_photo = "https://example.com/second.jpg"

    second_response = authenticated_client.post(
        COMPLETION_URL,
        {"courseId": course.id, "userPhoto": second_photo},
        format="json",
    )

    assert second_response.status_code == 200
    assert CompletionCard.objects.filter(user=user, course=course).count() == 1
    card = CompletionCard.objects.get(user=user, course=course)
    assert second_response.data["data"] == {
        "cardId": first_response.data["data"]["cardId"],
        "cardImageUrl": second_photo,
    }
    assert card.user_photo == second_photo
    assert card.card_image_url == second_photo


def test_list_completion_cards_returns_own_cards_newest_first(
    authenticated_client, user, other_user
):
    older_course = Course.objects.create(name="오래된 코스")
    newer_course = Course.objects.create(name="최신 코스")
    other_course = Course.objects.create(name="다른 사용자 코스")
    older_card = CompletionCard.objects.create(
        user=user,
        course=older_course,
        user_photo="https://example.com/older.jpg",
        card_image_url="https://example.com/older.jpg",
    )
    newer_card = CompletionCard.objects.create(
        user=user,
        course=newer_course,
        user_photo="https://example.com/newer.jpg",
        card_image_url="https://example.com/newer.jpg",
    )
    CompletionCard.objects.create(
        user=other_user,
        course=other_course,
        user_photo="https://example.com/other.jpg",
        card_image_url="https://example.com/other.jpg",
    )
    CompletionCard.objects.filter(pk=older_card.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    response = authenticated_client.get(CARDS_URL)

    assert response.status_code == 200
    cards = response.data["data"]["cards"]
    assert [card["cardId"] for card in cards] == [newer_card.id, older_card.id]
    assert cards[0]["courseName"] == "최신 코스"
    assert cards[0]["date"] == newer_card.created_at
    assert cards[0]["imageUrl"] == "https://example.com/newer.jpg"


@override_settings(CARD_SHARE_BASE_URL="https://eodiganam.app/cards")
def test_share_completion_card(authenticated_client, user, course):
    card = CompletionCard.objects.create(
        user=user,
        course=course,
        user_photo="https://example.com/card.jpg",
        card_image_url="https://example.com/card.jpg",
    )

    response = authenticated_client.post(f"{CARDS_URL}/{card.id}/share")

    assert response.status_code == 200
    assert response.data["data"] == {
        "shareUrl": f"https://eodiganam.app/cards/{card.id}"
    }


def test_share_completion_card_not_found(authenticated_client):
    response = authenticated_client.post(f"{CARDS_URL}/999999/share")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "COMMON_404"


def test_share_completion_card_rejects_other_users_card(
    authenticated_client, other_user, course
):
    card = CompletionCard.objects.create(
        user=other_user,
        course=course,
        user_photo="https://example.com/private.jpg",
        card_image_url="https://example.com/private.jpg",
    )

    response = authenticated_client.post(f"{CARDS_URL}/{card.id}/share")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "COMMON_404"
