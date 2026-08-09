from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import User
from interactions.models import Bookmark
from interactions.services import toggle_bookmark
from places.models import TouristSpot


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="bookmark-user",
        email="bookmark@example.com",
        nickname="찜한 여행자",
        password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def spot():
    return TouristSpot.objects.create(
        content_id="bookmark-spot",
        name="찜하기 장소",
        category=TouristSpot.Category.ATTRACTION,
        address="전라남도 여수시",
        description="찜하기 테스트 장소",
        latitude=Decimal("34.7600000"),
        longitude=Decimal("127.6600000"),
        synced_at=timezone.now(),
    )


def test_toggle_bookmark(authenticated_client, user, spot):
    url = f"/api/v1/places/{spot.id}/like"
    first = authenticated_client.post(url)

    assert first.data["data"] == {"liked": True}
    assert Bookmark.objects.filter(user=user, place=spot).exists()

    second = authenticated_client.post(url)

    assert second.data["data"] == {"liked": False}
    assert not Bookmark.objects.filter(user=user, place=spot).exists()


def test_bookmark_place_not_found(authenticated_client):
    response = authenticated_client.post("/api/v1/places/999999/like")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "PLACE_NOT_FOUND"


def test_toggle_bookmark_handles_concurrent_create(user, spot):
    with patch(
        "interactions.services.Bookmark.objects.create",
        side_effect=IntegrityError,
    ):
        liked = toggle_bookmark(place_id=spot.id, user=user)

    assert liked is True


def test_toggle_bookmark_requires_authentication(api_client, spot):
    response = api_client.post(f"/api/v1/places/{spot.id}/like")

    assert response.status_code == 401
