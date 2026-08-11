from rest_framework import serializers

from common.serializers import PageQuerySerializer
from reviews.models import Review


class ReviewCreateSerializer(serializers.Serializer):
    targetId = serializers.IntegerField()
    rating = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=5
    )
    text = serializers.CharField()
    photos = serializers.ListField(child=serializers.URLField(), required=False, default=list)
    visitDate = serializers.DateField(required=False, allow_null=True, default=None)
    visitWeather = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewListQuerySerializer(PageQuerySerializer):
    targetId = serializers.IntegerField()
    sort = serializers.ChoiceField(choices=["latest", "rating"], required=False, default="latest")


class ReviewSummaryQuerySerializer(serializers.Serializer):
    targetId = serializers.IntegerField()


class ReviewListItemSerializer(serializers.ModelSerializer):
    reviewId = serializers.CharField(source="id")
    author = serializers.CharField(source="user.nickname")
    text = serializers.CharField(source="content")
    photos = serializers.SerializerMethodField()
    visitWeather = serializers.CharField(source="weather_at_visit")

    class Meta:
        model = Review
        fields = ("reviewId", "author", "rating", "text", "photos", "visitWeather")

    def get_photos(self, obj) -> list[str]:
        return [photo.image_url for photo in obj.photos.all()]


class ReviewReportSerializer(serializers.Serializer):
    reason = serializers.CharField()


class ReviewsErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField()
