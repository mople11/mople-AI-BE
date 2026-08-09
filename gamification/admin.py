from django.contrib import admin

from gamification.models import CompletionCard, HiddenCourse, Stamp


@admin.register(Stamp)
class StampAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "city_code", "acquired_at")
    search_fields = ("user__nickname", "city_code")


@admin.register(HiddenCourse)
class HiddenCourseAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "rarity", "unlock_condition")
    search_fields = ("course__name", "rarity")


@admin.register(CompletionCard)
class CompletionCardAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "card_image_url", "created_at")
    search_fields = ("user__nickname", "course__name")
