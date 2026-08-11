from django.conf import settings
from django.urls import resolve


def test_project_uses_mysql() -> None:
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.mysql"


def test_admin_url_is_configured() -> None:
    assert resolve("/admin/").url_name == "index"


def test_cors_middleware_installed() -> None:
    assert "corsheaders.middleware.CorsMiddleware" in settings.MIDDLEWARE
    assert "corsheaders" in settings.INSTALLED_APPS


def test_cors_allows_configured_origin(api_client) -> None:
    origin = settings.CORS_ALLOWED_ORIGINS[0]
    response = api_client.get("/api/schema/", HTTP_ORIGIN=origin)
    assert response["Access-Control-Allow-Origin"] == origin


def test_cors_rejects_unconfigured_origin(api_client) -> None:
    response = api_client.get("/api/schema/", HTTP_ORIGIN="http://not-allowed.example")
    assert "Access-Control-Allow-Origin" not in response
