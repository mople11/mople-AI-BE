from decimal import Decimal

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import User
from courses.models import Course, CoursePlace, CourseProgress
from places.models import TouristSpot


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="course-traveler",
        email="course-traveler@example.com",
        nickname="코스 여행자",
        password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def course():
    course = Course.objects.create(
        name="여수 바다 코스",
        duration_minutes=180,
        distance_km=Decimal("5.20"),
        recommend_reason="바다를 따라 걷는 코스",
    )
    coordinates = [
        ("34.7600000", "127.6600000"),
        ("34.7610000", "127.6610000"),
        ("34.7620000", "127.6620000"),
    ]
    for order, (latitude, longitude) in enumerate(coordinates):
        spot = TouristSpot.objects.create(
            content_id=f"course-spot-{order}",
            name=f"코스 장소 {order}",
            category=TouristSpot.Category.ATTRACTION,
            address="전라남도 여수시",
            description="코스 테스트 장소",
            latitude=Decimal(latitude),
            longitude=Decimal(longitude),
            synced_at=timezone.now(),
        )
        CoursePlace.objects.create(
            course=course,
            place=spot,
            order=order,
        )
    return course


def course_url(course_id, action):
    return f"/api/v1/courses/{course_id}/{action}"


def check_in_locations(course):
    return [
        {"lat": float(course_place.place.latitude), "lng": float(course_place.place.longitude)}
        for course_place in course.places.select_related("place").order_by("order")
    ]


def test_save_course_success(authenticated_client, user, course):
    response = authenticated_client.post(course_url(course.id, "save"))

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"saved": True},
        "error": None,
    }
    course.refresh_from_db()
    assert course.status == Course.Status.SAVED
    assert CourseProgress.objects.get(user=user, course=course).status == CourseProgress.Status.SAVED


def test_save_course_not_found(authenticated_client):
    response = authenticated_client.post(course_url(999999, "save"))

    assert response.status_code == 404
    assert response.data["error"]["code"] == "COURSE_NOT_FOUND"


def test_start_course_success(authenticated_client, user, course):
    response = authenticated_client.post(course_url(course.id, "start"))

    assert response.status_code == 200
    progress = CourseProgress.objects.get(user=user, course=course)
    assert progress.status == CourseProgress.Status.IN_PROGRESS
    assert progress.started_at is not None
    assert parse_datetime(response.json()["data"]["startedAt"]) == progress.started_at


def test_start_course_not_found(authenticated_client):
    response = authenticated_client.post(course_url(999999, "start"))

    assert response.status_code == 404
    assert response.data["error"]["code"] == "COURSE_NOT_FOUND"


def test_complete_course_success(authenticated_client, user, course):
    response = authenticated_client.post(
        course_url(course.id, "complete"),
        {"checkInLocations": check_in_locations(course)},
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"completed": True, "cardId": None},
        "error": None,
    }
    progress = CourseProgress.objects.get(user=user, course=course)
    assert progress.status == CourseProgress.Status.COMPLETED
    assert progress.completed_at is not None


def test_complete_course_outside_radius_preserves_progress(
    authenticated_client,
    user,
    course,
):
    progress = CourseProgress.objects.create(
        user=user,
        course=course,
        status=CourseProgress.Status.IN_PROGRESS,
        started_at=timezone.now(),
    )
    locations = check_in_locations(course)
    locations[1]["lat"] += 0.01

    response = authenticated_client.post(
        course_url(course.id, "complete"),
        {"checkInLocations": locations},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "LOCATION_MISMATCH"
    progress.refresh_from_db()
    assert progress.status == CourseProgress.Status.IN_PROGRESS
    assert progress.completed_at is None


def test_complete_course_location_count_mismatch(authenticated_client, course):
    response = authenticated_client.post(
        course_url(course.id, "complete"),
        {"checkInLocations": check_in_locations(course)[:2]},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "LOCATION_MISMATCH"


def test_complete_course_not_found(authenticated_client):
    response = authenticated_client.post(
        course_url(999999, "complete"),
        {"checkInLocations": [{"lat": 34.8, "lng": 126.4}]},
        format="json",
    )

    assert response.status_code == 404
    assert response.data["error"]["code"] == "COURSE_NOT_FOUND"


def test_complete_course_rejects_empty_locations(authenticated_client, course):
    response = authenticated_client.post(
        course_url(course.id, "complete"),
        {"checkInLocations": []},
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


@pytest.mark.parametrize(
    "location",
    [
        {"lat": 91, "lng": 127},
        {"lat": 34, "lng": 181},
    ],
)
def test_complete_course_rejects_invalid_coordinate_range(
    authenticated_client,
    course,
    location,
):
    response = authenticated_client.post(
        course_url(course.id, "complete"),
        {"checkInLocations": [location]},
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_share_course_success(authenticated_client, course, settings):
    settings.COURSE_SHARE_BASE_URL = "https://eodiganam.app/courses"

    response = authenticated_client.post(course_url(course.id, "share"))

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {"shareUrl": f"https://eodiganam.app/courses/{course.id}"},
        "error": None,
    }


def test_share_course_not_found(authenticated_client):
    response = authenticated_client.post(course_url(999999, "share"))

    assert response.status_code == 404
    assert response.data["error"]["code"] == "COURSE_NOT_FOUND"


def test_course_endpoint_requires_authentication(api_client, course):
    response = api_client.post(course_url(course.id, "save"))

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"
