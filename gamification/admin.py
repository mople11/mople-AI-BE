from django.contrib import admin

from gamification.models import Stamp


@admin.register(Stamp)
class StampAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "city_code", "acquired_at")
    search_fields = ("user__nickname", "city_code")
