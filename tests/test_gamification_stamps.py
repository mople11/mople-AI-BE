from unittest.mock import patch

import pytest

from accounts.models import User
from gamification.models import Stamp


pytestmark = pytest.mark.django_db

CHECKIN_URL = "/api/v1/stamps/checkin"
STAMPS_URL = "/api/v1/stamps"


@pytest.fixture
def user():
    return User.objects.create_user(
        username="stamp-collector",
        email="stamp-collector@example.com",
        nickname="스탬프 수집가",
        password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


def test_checkin_success(authenticated_client, user):
    with patch(
        "gamification.services.KakaoLocalClient.get_city_code",
        return_value="46130",
    ):
        response = authenticated_client.post(
            CHECKIN_URL, {"lat": 34.76, "lng": 127.66}
        )

    assert response.status_code == 200
    assert response.data["data"] == {"stampAcquired": True, "cityCode": "46130"}
    assert Stamp.objects.filter(user=user, city_code="46130").exists()


def test_checkin_already_acquired(authenticated_client, user):
    Stamp.objects.create(user=user, city_code="46130")

    with patch(
        "gamification.services.KakaoLocalClient.get_city_code",
        return_value="46130",
    ):
        response = authenticated_client.post(
            CHECKIN_URL, {"lat": 34.76, "lng": 127.66}
        )

    assert response.status_code == 200
    assert response.data["data"] == {"stampAcquired": False, "cityCode": "46130"}
    assert Stamp.objects.filter(user=user, city_code="46130").count() == 1


def test_checkin_out_of_region(authenticated_client):
    with patch(
        "gamification.services.KakaoLocalClient.get_city_code",
        return_value=None,
    ):
        response = authenticated_client.post(
            CHECKIN_URL, {"lat": 37.5, "lng": 127.0}
        )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "OUT_OF_REGION"


def test_checkin_requires_authentication(api_client):
    response = api_client.post(CHECKIN_URL, {"lat": 34.76, "lng": 127.66})
    assert response.status_code == 401


def test_stampbook_status(authenticated_client, user):
    Stamp.objects.create(user=user, city_code="46130")
    Stamp.objects.create(user=user, city_code="46110")

    response = authenticated_client.get(STAMPS_URL)

    assert response.status_code == 200
    data = response.data["data"]
    assert sorted(data["collected"]) == ["46110", "46130"]
    assert data["totalCount"] == 22
    assert data["progress"] == round(2 / 22 * 100)


def test_stampbook_status_empty(authenticated_client):
    response = authenticated_client.get(STAMPS_URL)

    assert response.status_code == 200
    assert response.data["data"] == {
        "collected": [],
        "totalCount": 22,
        "progress": 0,
    }
