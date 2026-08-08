from django.contrib import admin

from reviews.models import Review, ReviewPhoto, ReviewReaction, ReviewReport


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "place", "rating", "like_count")
    search_fields = ("user__nickname", "place__name", "content")


admin.site.register(ReviewPhoto)
admin.site.register(ReviewReaction)
admin.site.register(ReviewReport)
