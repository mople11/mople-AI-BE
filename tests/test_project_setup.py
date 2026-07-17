from django.conf import settings
from django.urls import resolve


def test_project_uses_mysql() -> None:
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.mysql"


def test_admin_url_is_configured() -> None:
    assert resolve("/admin/").url_name == "index"
