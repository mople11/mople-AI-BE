from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from courses.models import Course


class LocationQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class WeatherDataSerializer(serializers.Serializer):
    weatherType = serializers.CharField()
    temp = serializers.FloatField()
    icon = serializers.CharField()


class HomeWeatherSerializer(serializers.Serializer):
    type = serializers.CharField()
    temp = serializers.FloatField()
    icon = serializers.CharField()


class RecommendedCourseSerializer(serializers.ModelSerializer):
    courseId = serializers.CharField(source="id")
    duration = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ("courseId", "name", "duration", "distance", "thumbnail")

    @extend_schema_field(OpenApiTypes.STR)
    def get_duration(self, obj) -> str | None:
        if obj.duration_minutes is None:
            return None
        hours, minutes = divmod(obj.duration_minutes, 60)
        if hours and minutes:
            return f"{hours}시간 {minutes}분"
        if hours:
            return f"{hours}시간"
        return f"{minutes}분"

    @extend_schema_field(OpenApiTypes.STR)
    def get_distance(self, obj) -> str | None:
        if obj.distance_km is None:
            return None
        return f"{round(float(obj.distance_km), 1)}km"

    @extend_schema_field(OpenApiTypes.URI)
    def get_thumbnail(self, obj) -> str | None:
        if not obj.home_places:
            return None
        primary_images = obj.home_places[0].place.primary_images
        return primary_images[0].image_url if primary_images else None


class UnlockBannerSerializer(serializers.Serializer):
    available = serializers.BooleanField()


class HomeDataSerializer(serializers.Serializer):
    weather = HomeWeatherSerializer()
    recommendedCourses = RecommendedCourseSerializer(many=True)
    unlockBanner = UnlockBannerSerializer()


class HomeErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField()
