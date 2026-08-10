from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import User
from common.exceptions import ApiError, ErrorCode
from courses.models import Course, CourseProgress
from gamification.models import Stamp
from interactions.models import Bookmark
from places.models import TouristSpot
from reviews.models import Review
from mypage.services import update_profile


pytestmark = pytest.mark.django_db


@pytest.fixture
def users():
    user_a = User.objects.create_user(
        username="mypage-a",
        email="mypage-a@example.com",
        nickname="마이페이지 A",
        password="safe-password-123",
    )
    user_b = User.objects.create_user(
        username="mypage-b",
        email="mypage-b@example.com",
        nickname="마이페이지 B",
        password="safe-password-123",
    )
    return user_a, user_b


@pytest.fixture
def authenticated_client(api_client, users):
    user_a, _ = users
    api_client.force_authenticate(user=user_a)
    return api_client


def create_spot(*, content_id, name):
    return TouristSpot.objects.create(
        content_id=content_id,
        name=name,
        category=TouristSpot.Category.ATTRACTION,
        address="전라남도 여수시",
        description="마이페이지 테스트 장소",
        latitude=Decimal("34.7600000"),
        longitude=Decimal("127.6600000"),
        synced_at=timezone.now(),
    )


def test_get_profile_summary_counts_authenticated_users_data(
    authenticated_client, users
):
    user_a, user_b = users
    course_a = Course.objects.create(name="A 완주 코스")
    course_b = Course.objects.create(name="B 완주 코스")
    CourseProgress.objects.create(
        user=user_a, course=course_a, status=CourseProgress.Status.COMPLETED
    )
    CourseProgress.objects.create(
        user=user_b, course=course_b, status=CourseProgress.Status.COMPLETED
    )
    Stamp.objects.create(user=user_a, city_code="46130")
    Stamp.objects.create(user=user_b, city_code="46110")
    spot = create_spot(content_id="mypage-summary", name="요약 장소")
    Review.objects.create(user=user_a, place=spot, rating=5, content="좋아요")
    Review.objects.create(user=user_b, place=spot, rating=4, content="괜찮아요")

    response = authenticated_client.get("/api/v1/users/me")

    assert response.status_code == 200
    assert response.data["data"] == {
        "profile": {"nickname": "마이페이지 A", "profileImg": None},
        "stats": {"completedCourses": 1, "stamps": 1, "reviews": 1},
    }


def test_patch_profile_and_reject_duplicate_nickname(authenticated_client, users):
    user_a, user_b = users

    response = authenticated_client.patch(
        "/api/v1/users/me",
        {"nickname": "새 닉네임", "profileImg": "https://example.com/profile.jpg"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"] == {"updated": True}
    user_a.refresh_from_db()
    assert user_a.nickname == "새 닉네임"
    assert user_a.profile_img == "https://example.com/profile.jpg"

    duplicate = authenticated_client.patch(
        "/api/v1/users/me", {"nickname": user_b.nickname}, format="json"
    )

    assert duplicate.status_code == 409
    assert duplicate.data["error"]["code"] == "NICKNAME_DUPLICATE"


def test_patch_profile_requires_at_least_one_field(authenticated_client):
    response = authenticated_client.patch("/api/v1/users/me", {}, format="json")

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_patch_profile_blank_image_is_stored_as_null(authenticated_client, users):
    user_a, _ = users
    user_a.profile_img = "https://example.com/old-profile.jpg"
    user_a.save(update_fields=["profile_img"])

    response = authenticated_client.patch(
        "/api/v1/users/me", {"profileImg": ""}, format="json"
    )

    assert response.status_code == 200
    user_a.refresh_from_db()
    assert user_a.profile_img is None


def test_update_profile_converts_integrity_error_to_nickname_duplicate(users):
    user_a, _ = users

    with patch.object(User, "save", side_effect=IntegrityError):
        with pytest.raises(ApiError) as exc_info:
            update_profile(user=user_a, nickname="동시 변경 닉네임")

    assert exc_info.value.error_code is ErrorCode.NICKNAME_DUPLICATE


def test_update_profile_without_fields_is_explicit_noop(users):
    user_a, _ = users

    with patch.object(User, "save") as mock_save:
        updated = update_profile(user=user_a)

    assert updated is True
    mock_save.assert_not_called()


def test_mypage_lists_only_authenticated_users_data(authenticated_client, users):
    user_a, user_b = users
    course_a = Course.objects.create(name="A 저장 코스")
    course_b = Course.objects.create(name="B 저장 코스")
    CourseProgress.objects.create(
        user=user_a, course=course_a, status=CourseProgress.Status.SAVED
    )
    CourseProgress.objects.create(
        user=user_b, course=course_b, status=CourseProgress.Status.IN_PROGRESS
    )
    spot_a = create_spot(content_id="mypage-a-spot", name="A 장소")
    spot_b = create_spot(content_id="mypage-b-spot", name="B 장소")
    review_a = Review.objects.create(
        user=user_a, place=spot_a, rating=5, content="A 후기"
    )
    Review.objects.create(user=user_b, place=spot_b, rating=3, content="B 후기")
    Bookmark.objects.create(user=user_a, place=spot_a)
    Bookmark.objects.create(user=user_b, place=spot_b)

    courses_response = authenticated_client.get("/api/v1/users/me/courses")
    reviews_response = authenticated_client.get("/api/v1/users/me/reviews")
    likes_response = authenticated_client.get("/api/v1/users/me/likes")

    assert courses_response.status_code == 200
    assert courses_response.data["data"]["courses"] == [
        {"courseId": str(course_a.id), "name": "A 저장 코스"}
    ]
    assert reviews_response.status_code == 200
    assert reviews_response.data["data"]["reviews"] == [
        {"reviewId": str(review_a.id), "targetName": "A 장소", "rating": 5}
    ]
    assert likes_response.status_code == 200
    assert likes_response.data["data"]["places"] == [
        {"placeId": str(spot_a.id), "name": "A 장소"}
    ]


@pytest.mark.parametrize(
    "method,url",
    [
        ("get", "/api/v1/users/me"),
        ("patch", "/api/v1/users/me"),
        ("get", "/api/v1/users/me/courses"),
        ("get", "/api/v1/users/me/reviews"),
        ("get", "/api/v1/users/me/likes"),
    ],
)
def test_mypage_requires_authentication(api_client, method, url):
    response = getattr(api_client, method)(url, {}, format="json")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"
