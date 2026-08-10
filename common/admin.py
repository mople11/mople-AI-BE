from django.contrib import admin

from common.models import UserSettings


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "push_notification_enabled",
        "golden_hour_notification_enabled",
        "language",
        "location_permission_granted",
        "updated_at",
    )
    list_filter = (
        "push_notification_enabled",
        "golden_hour_notification_enabled",
        "language",
        "location_permission_granted",
    )
    search_fields = ("user__username", "user__email", "user__nickname")
    readonly_fields = ("created_at", "updated_at")
