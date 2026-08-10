import pytest

from accounts.models import User
from common.models import UserSettings


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="settings-user",
        email="settings@example.com",
        nickname="설정 사용자",
        password="safe-password-123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


def test_get_settings_creates_defaults(authenticated_client, user):
    assert not UserSettings.objects.filter(user=user).exists()

    response = authenticated_client.get("/api/v1/settings")

    assert response.status_code == 200
    assert response.data == {
        "success": True,
        "data": {
            "notifications": {"push": True, "goldenHour": True},
            "language": "ko",
            "permissions": {"location": False},
        },
        "error": None,
    }
    assert UserSettings.objects.filter(user=user).exists()


def test_get_settings_requires_authentication(api_client):
    response = api_client.get("/api/v1/settings")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"


def test_patch_push_only_preserves_other_fields(authenticated_client, user):
    response = authenticated_client.patch(
        "/api/v1/settings",
        {"notifications": {"push": False}},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"] == {"updated": True}
    get_response = authenticated_client.get("/api/v1/settings")
    assert get_response.data["data"] == {
        "notifications": {"push": False, "goldenHour": True},
        "language": "ko",
        "permissions": {"location": False},
    }


def test_patch_language_and_location_permission_individually(authenticated_client, user):
    language_response = authenticated_client.patch(
        "/api/v1/settings", {"language": "en"}, format="json"
    )

    assert language_response.status_code == 200
    user_settings = UserSettings.objects.get(user=user)
    assert user_settings.language == "en"
    assert user_settings.push_notification_enabled is True

    location_response = authenticated_client.patch(
        "/api/v1/settings",
        {"permissions": {"location": True}},
        format="json",
    )

    assert location_response.status_code == 200
    user_settings.refresh_from_db()
    assert user_settings.location_permission_granted is True
    assert user_settings.language == "en"


def test_patch_multiple_settings(authenticated_client, user):
    response = authenticated_client.patch(
        "/api/v1/settings",
        {
            "notifications": {"push": False, "goldenHour": False},
            "language": "ja",
            "permissions": {"location": True},
        },
        format="json",
    )

    assert response.status_code == 200
    user_settings = UserSettings.objects.get(user=user)
    assert user_settings.push_notification_enabled is False
    assert user_settings.golden_hour_notification_enabled is False
    assert user_settings.language == "ja"
    assert user_settings.location_permission_granted is True


def test_patch_rejects_empty_body(authenticated_client):
    response = authenticated_client.patch(
        "/api/v1/settings", {}, format="json"
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_patch_rejects_empty_nested_notifications(authenticated_client):
    response = authenticated_client.patch(
        "/api/v1/settings", {"notifications": {}}, format="json"
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_patch_rejects_unknown_field(authenticated_client):
    response = authenticated_client.patch(
        "/api/v1/settings",
        {"notifications": {"pushh": True}},
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "pushh" in response.data["error"]["details"]["notifications"]


def test_patch_rejects_non_object_nested_value(authenticated_client):
    response = authenticated_client.patch(
        "/api/v1/settings", {"notifications": 5}, format="json"
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "notifications" in response.data["error"]["details"]


def test_patch_rejects_non_object_body(authenticated_client):
    response = authenticated_client.patch(
        "/api/v1/settings", 5, format="json"
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"


def test_patch_rejects_invalid_language(authenticated_client):
    response = authenticated_client.patch(
        "/api/v1/settings", {"language": "fr"}, format="json"
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"
    assert "language" in response.data["error"]["details"]
    assert "notifications" not in response.data["error"]["details"]


def test_patch_settings_requires_authentication(api_client):
    response = api_client.patch(
        "/api/v1/settings", {"language": "en"}, format="json"
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"
