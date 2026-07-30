from django.contrib import admin

from places.models import TouristSpot, TouristSpotImage


class TouristSpotImageInline(admin.TabularInline):
    model = TouristSpotImage
    extra = 0


@admin.register(TouristSpot)
class TouristSpotAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "sigungu", "parking_available", "synced_at")
    list_filter = ("category", "parking_available")
    search_fields = ("name", "content_id", "address")
    inlines = [TouristSpotImageInline]


@admin.register(TouristSpotImage)
class TouristSpotImageAdmin(admin.ModelAdmin):
    list_display = ("id", "spot", "is_primary", "order")

