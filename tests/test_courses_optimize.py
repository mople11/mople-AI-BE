from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from accounts.models import User
from courses.models import CoursePlace
from places.models import TouristSpot


pytestmark = pytest.mark.django_db
OPTIMIZE_URL = "/api/v1/courses/optimize"


@pytest.fixture
def user():
    return User.objects.create_user(
        username="route-optimizer",
        email="route-optimizer@example.com",
        nickname="동선 최적화 사용자",
        password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def spots():
    coordinates = [
        (Decimal("34.7600000"), Decimal("127.6600000")),
        (Decimal("34.7700000"), Decimal("127.6700000")),
        (Decimal("34.7800000"), Decimal("127.6800000")),
    ]
    return [
        TouristSpot.objects.create(
            content_id=f"optimize-{index}",
            name=f"최적화 장소 {index}",
            category=TouristSpot.Category.ATTRACTION,
            address="전라남도 여수시",
            latitude=latitude,
            longitude=longitude,
            synced_at=timezone.now(),
        )
        for index, (latitude, longitude) in enumerate(coordinates, start=1)
    ]


def payload(spots, *, transport="차량"):
    return {
        "placeIds": [str(spot.id) for spot in spots],
        "transport": transport,
    }


def test_optimize_three_places_returns_shortest_one_way_route(
    authenticated_client,
    spots,
):
    coords = [(spot.latitude, spot.longitude) for spot in spots]
    durations = {
        (coords[0], coords[1]): 9,
        (coords[0], coords[2]): 8,
        (coords[1], coords[0]): 9,
        (coords[1], coords[2]): 1,
        (coords[2], coords[0]): 1,
        (coords[2], coords[1]): 9,
    }

    def get_traffic(*, origin, destination):
        return SimpleNamespace(eta_min=durations[(origin, destination)])

    count_before = CoursePlace.objects.count()
    with patch(
        "courses.services.KakaoMobilityClient.get_traffic",
        side_effect=get_traffic,
    ) as mock_get_traffic:
        response = authenticated_client.post(
            OPTIMIZE_URL, payload(spots), format="json"
        )

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {
            "orderedPlaces": [str(spots[1].id), str(spots[2].id), str(spots[0].id)],
            "segmentTimes": [1, 1],
            "totalTime": 2,
            "route": {},
        },
        "error": None,
    }
    assert len(response.data["data"]["segmentTimes"]) == len(spots) - 1
    assert response.data["data"]["totalTime"] == sum(
        response.data["data"]["segmentTimes"]
    )
    assert mock_get_traffic.call_count == len(spots) * (len(spots) - 1)
    assert CoursePlace.objects.count() == count_before


def test_optimize_two_places_returns_one_segment(authenticated_client, spots):
    selected = spots[:2]
    with patch(
        "courses.services.KakaoMobilityClient.get_traffic",
        side_effect=[SimpleNamespace(eta_min=7), SimpleNamespace(eta_min=3)],
    ) as mock_get_traffic:
        response = authenticated_client.post(
            OPTIMIZE_URL, payload(selected, transport="도보"), format="json"
        )

    assert response.status_code == 200
    assert response.data["data"] == {
        "orderedPlaces": [str(selected[1].id), str(selected[0].id)],
        "segmentTimes": [3],
        "totalTime": 3,
        "route": {},
    }
    assert sorted(response.data["data"]["orderedPlaces"]) == sorted(
        payload(selected)["placeIds"]
    )
    assert mock_get_traffic.call_count == 2


def test_optimize_preserves_duplicate_place_ids(authenticated_client, spots):
    request_data = payload(spots[:2])
    request_data["placeIds"].append(request_data["placeIds"][0])

    count_before = CoursePlace.objects.count()
    with patch(
        "courses.services.KakaoMobilityClient.get_traffic",
        return_value=SimpleNamespace(eta_min=1),
    ) as mock_get_traffic:
        response = authenticated_client.post(
            OPTIMIZE_URL, request_data, format="json"
        )

    assert response.status_code == 200
    assert len(response.data["data"]["orderedPlaces"]) == len(
        request_data["placeIds"]
    )
    assert sorted(response.data["data"]["orderedPlaces"]) == sorted(
        request_data["placeIds"]
    )
    assert len(response.data["data"]["segmentTimes"]) == 2
    assert mock_get_traffic.call_count == 6
    assert CoursePlace.objects.count() == count_before


def test_optimize_rejects_more_than_eight_places(authenticated_client):
    request_data = {
        "placeIds": [str(index) for index in range(1, 10)],
        "transport": "차량",
    }

    with patch(
        "courses.services.KakaoMobilityClient.get_traffic"
    ) as mock_get_traffic:
        response = authenticated_client.post(
            OPTIMIZE_URL, request_data, format="json"
        )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    mock_get_traffic.assert_not_called()


@pytest.mark.parametrize("place_count", [0, 1])
def test_optimize_requires_at_least_two_places(
    authenticated_client,
    spots,
    place_count,
):
    response = authenticated_client.post(
        OPTIMIZE_URL, payload(spots[:place_count]), format="json"
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "MIN_PLACE_REQUIRED"


def test_optimize_rejects_unknown_place(authenticated_client, spots):
    request_data = payload(spots[:1])
    request_data["placeIds"].append("999999")

    response = authenticated_client.post(
        OPTIMIZE_URL, request_data, format="json"
    )

    assert response.status_code == 404
    assert response.data["error"]["code"] == "PLACE_NOT_FOUND"


def test_optimize_rejects_non_numeric_place_id(authenticated_client, spots):
    request_data = payload(spots[:1])
    request_data["placeIds"].append("not-a-place-id")

    response = authenticated_client.post(
        OPTIMIZE_URL, request_data, format="json"
    )

    assert response.status_code == 404
    assert response.data["error"]["code"] == "PLACE_NOT_FOUND"


def test_optimize_returns_route_calc_failed_when_traffic_fails(
    authenticated_client,
    spots,
):
    with patch(
        "courses.services.KakaoMobilityClient.get_traffic", return_value=None
    ) as mock_get_traffic:
        response = authenticated_client.post(
            OPTIMIZE_URL, payload(spots[:2]), format="json"
        )

    assert response.status_code == 500
    assert response.data["error"]["code"] == "ROUTE_CALC_FAILED"
    assert mock_get_traffic.call_count == 1


def test_optimize_rejects_invalid_transport(authenticated_client, spots):
    response = authenticated_client.post(
        OPTIMIZE_URL,
        payload(spots[:2], transport="자전거"),
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_optimize_requires_authentication(api_client, spots):
    response = api_client.post(
        OPTIMIZE_URL, payload(spots[:2]), format="json"
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"
