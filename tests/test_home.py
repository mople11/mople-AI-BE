from unittest.mock import Mock, patch

import pytest
import requests
from django.test import override_settings
from django.utils import timezone

from accounts.models import User
from courses.models import Course, CoursePlace
from gamification.models import HiddenCourse, UserHiddenCourseUnlock
from home.kma import KmaClient, WeatherData, latlng_to_grid
from home.serializers import HomeDataSerializer
from home.services import get_home_data
from places.models import TouristSpot, TouristSpotImage


LOCATION = {"lat": 34.885, "lng": 127.509}
WEATHER = WeatherData(weather_type="맑음", temp=23.4, icon="clear")


def create_spot(**overrides):
    values = {
        "content_id": "home-spot",
        "name": "홈 추천 장소",
        "category": TouristSpot.Category.ATTRACTION,
        "address": "전라남도 여수시",
        "description": "",
        "latitude": 34.885,
        "longitude": 127.509,
        "synced_at": timezone.now(),
    }
    values.update(overrides)
    return TouristSpot.objects.create(**values)


def create_user(username="home-user"):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="password123!",
        nickname=username,
    )


def test_latlng_to_grid_known_coordinates():
    assert latlng_to_grid(37.5665, 126.9780) == (61, 128)
    assert latlng_to_grid(34.885, 127.509) == (71, 70)


@override_settings(
    KMA_API_BASE_URL="https://kma.example/api",
    KMA_API_SERVICE_KEY="test-key",
    KMA_API_TIMEOUT_SEC=7,
)
@patch("home.kma.requests.get")
@patch.object(KmaClient, "_latest_base_datetime", return_value=("20260810", "1300"))
def test_kma_client_builds_request_and_parses_weather(mock_datetime, mock_get):
    response = Mock()
    response.json.return_value = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
            "body": {
                "items": {
                    "item": [
                        {"category": "T1H", "obsrValue": "23.4"},
                        {"category": "PTY", "obsrValue": "2"},
                    ]
                }
            },
        }
    }
    mock_get.return_value = response

    weather = KmaClient().get_current_weather(**LOCATION)

    assert weather == WeatherData(weather_type="비/눈", temp=23.4, icon="sleet")
    mock_get.assert_called_once_with(
        "https://kma.example/api/getUltraSrtNcst",
        params={
            "serviceKey": "test-key",
            "pageNo": 1,
            "numOfRows": 10,
            "dataType": "JSON",
            "base_date": "20260810",
            "base_time": "1300",
            "nx": 71,
            "ny": 70,
        },
        timeout=7,
    )
    response.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize(
    "payload",
    [
        {"response": {"header": {"resultCode": "03", "resultMsg": "NO_DATA"}}},
        {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": [{"category": "PTY", "obsrValue": "0"}]}},
            }
        },
    ],
)
@patch("home.kma.requests.get")
def test_kma_client_returns_none_for_api_error_or_missing_field(mock_get, payload):
    mock_get.return_value.json.return_value = payload

    assert KmaClient().get_current_weather(**LOCATION) is None


@patch("home.kma.requests.get", side_effect=requests.Timeout("timed out"))
def test_kma_client_returns_none_for_request_failure(mock_get):
    assert KmaClient().get_current_weather(**LOCATION) is None


@pytest.mark.django_db
@patch("home.services.KmaClient.get_current_weather", return_value=WEATHER)
def test_current_weather_success(mock_weather, api_client):
    response = api_client.get("/api/v1/weather/current", LOCATION)

    assert response.status_code == 200
    assert response.data["data"] == {
        "weatherType": "맑음",
        "temp": 23.4,
        "icon": "clear",
    }
    mock_weather.assert_called_once_with(**LOCATION)


@pytest.mark.django_db
@patch("home.services.KmaClient.get_current_weather", return_value=None)
def test_current_weather_failure(mock_weather, api_client):
    response = api_client.get("/api/v1/weather/current", LOCATION)

    assert response.status_code == 502
    assert response.data["error"]["code"] == "WEATHER_FETCH_FAILED"


@pytest.mark.django_db
@pytest.mark.parametrize("query", [{}, {"lat": 100, "lng": 127.509}])
def test_current_weather_rejects_invalid_location(api_client, query):
    response = api_client.get("/api/v1/weather/current", query)

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


@pytest.mark.django_db
@patch("home.services.KmaClient.get_current_weather", return_value=WEATHER)
def test_home_success_returns_latest_saved_courses(mock_weather, api_client):
    older = Course.objects.create(
        name="오래된 저장 코스",
        status=Course.Status.SAVED,
        duration_minutes=90,
        distance_km=12.34,
    )
    Course.objects.create(name="임시 코스", status=Course.Status.TEMP)
    newer = Course.objects.create(
        name="최신 저장 코스",
        status=Course.Status.SAVED,
        duration_minutes=45,
        distance_km=3,
    )
    spot = create_spot()
    CoursePlace.objects.create(course=newer, place=spot, order=1)
    TouristSpotImage.objects.create(
        spot=spot,
        image_url="https://example.com/home.jpg",
        is_primary=True,
    )

    response = api_client.get("/api/v1/home", LOCATION)

    assert response.status_code == 200
    data = response.data["data"]
    assert data["weather"] == {"type": "맑음", "temp": 23.4, "icon": "clear"}
    assert [course["courseId"] for course in data["recommendedCourses"]] == [
        str(newer.id),
        str(older.id),
    ]
    assert data["recommendedCourses"][0] == {
        "courseId": str(newer.id),
        "name": "최신 저장 코스",
        "duration": "45분",
        "distance": "3.0km",
        "thumbnail": "https://example.com/home.jpg",
    }
    assert data["recommendedCourses"][1]["duration"] == "1시간 30분"
    assert data["recommendedCourses"][1]["thumbnail"] is None
    assert data["unlockBanner"] == {"available": False}


@pytest.mark.django_db
@patch("home.services.KmaClient.get_current_weather", return_value=WEATHER)
def test_home_recommended_course_queries_are_constant(
    mock_weather, django_assert_num_queries
):
    for index in range(5):
        course = Course.objects.create(
            name=f"추천 코스 {index}", status=Course.Status.SAVED
        )
        spot = create_spot(content_id=f"home-spot-{index}")
        CoursePlace.objects.create(course=course, place=spot, order=1)
        TouristSpotImage.objects.create(
            spot=spot,
            image_url=f"https://example.com/home-{index}.jpg",
            is_primary=True,
        )

    with django_assert_num_queries(4):
        data = get_home_data(
            user=Mock(is_authenticated=False),
            **LOCATION,
        )
        serialized = HomeDataSerializer(data).data

    assert len(serialized["recommendedCourses"]) == 5


@pytest.mark.django_db
@patch("home.services.KmaClient.get_current_weather", return_value=None)
def test_home_weather_failure(mock_weather, api_client):
    response = api_client.get("/api/v1/home", LOCATION)

    assert response.status_code == 502
    assert response.data["error"]["code"] == "WEATHER_FETCH_FAILED"


@pytest.mark.django_db
@patch("home.services.KmaClient.get_current_weather", return_value=WEATHER)
def test_unlock_banner_for_anonymous_user(mock_weather, api_client):
    response = api_client.get("/api/v1/home", LOCATION)
    assert response.data["data"]["unlockBanner"] == {"available": False}

    course = Course.objects.create(name="숨겨진 코스")
    HiddenCourse.objects.create(course=course, rarity=HiddenCourse.Rarity.COMMON)
    response = api_client.get("/api/v1/home", LOCATION)
    assert response.data["data"]["unlockBanner"] == {"available": True}


@pytest.mark.django_db
@patch("home.services.KmaClient.get_current_weather", return_value=WEATHER)
def test_unlock_banner_for_authenticated_user(mock_weather, api_client):
    user = create_user()
    first = HiddenCourse.objects.create(
        course=Course.objects.create(name="첫 번째 숨겨진 코스"),
        rarity=HiddenCourse.Rarity.COMMON,
    )
    second = HiddenCourse.objects.create(
        course=Course.objects.create(name="두 번째 숨겨진 코스"),
        rarity=HiddenCourse.Rarity.RARE,
    )
    UserHiddenCourseUnlock.objects.create(user=user, hidden_course=first)
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/v1/home", LOCATION)
    assert response.data["data"]["unlockBanner"] == {"available": True}

    UserHiddenCourseUnlock.objects.create(user=user, hidden_course=second)
    response = api_client.get("/api/v1/home", LOCATION)
    assert response.data["data"]["unlockBanner"] == {"available": False}
