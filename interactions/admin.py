from django.contrib import admin

from interactions.models import Bookmark


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "place", "created_at")
    search_fields = ("user__nickname", "place__name")
