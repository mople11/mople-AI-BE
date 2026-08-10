from django.conf import settings as django_settings
from django.db import models


class UserSettings(models.Model):
    class Language(models.TextChoices):
        KOREAN = "ko", "한국어"
        ENGLISH = "en", "English"
        JAPANESE = "ja", "日本語"
        CHINESE = "zh", "中文"

    user = models.OneToOneField(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    push_notification_enabled = models.BooleanField(default=True)
    golden_hour_notification_enabled = models.BooleanField(default=True)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.KOREAN
    )
    location_permission_granted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
