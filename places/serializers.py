from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from places.models import TouristSpot


class SpotSearchQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(required=False, allow_blank=True)
    category = serializers.ChoiceField(required=False, choices=["맛집", "관광지", "숙박", "축제"])
    region = serializers.CharField(required=False, allow_blank=True)
    sort = serializers.CharField(required=False, allow_blank=True)


class SpotDetailQuerySerializer(serializers.Serializer):
    latitude = serializers.DecimalField(required=False, max_digits=10, decimal_places=7, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(required=False, max_digits=10, decimal_places=7, min_value=-180, max_value=180)

    def validate(self, attrs):
        if ("latitude" in attrs) != ("longitude" in attrs):
            raise serializers.ValidationError("latitude와 longitude는 함께 입력해야 합니다.")
        return attrs


class TrafficQuerySerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, minimum, maximum in (
            ("origin.lat", -90, 90), ("origin.lng", -180, 180),
            ("destination.lat", -90, 90), ("destination.lng", -180, 180),
        ):
            self.fields[name] = serializers.FloatField(min_value=minimum, max_value=maximum)


class SpotSearchResultSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    category = serializers.CharField(source="get_category_display")
    location = serializers.CharField(source="address")
    rating = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = TouristSpot
        fields = ("id", "name", "category", "location", "rating", "thumbnail")

    @extend_schema_field(OpenApiTypes.INT)
    def get_rating(self, obj) -> int:
        return 0

    @extend_schema_field(OpenApiTypes.URI)
    def get_thumbnail(self, obj) -> str | None:
        image = obj.images.filter(is_primary=True).first()
        return image.image_url if image else None


class SpotDetailSerializer(serializers.ModelSerializer):
    placeId = serializers.IntegerField(source="id")
    category = serializers.CharField(source="get_category_display")
    images = serializers.SerializerMethodField()
    map = serializers.SerializerMethodField()
    distanceFromUser = serializers.SerializerMethodField()
    reviewSummary = serializers.SerializerMethodField()

    class Meta:
        model = TouristSpot
        fields = ("placeId", "name", "category", "description", "address", "hours", "images", "map", "distanceFromUser", "reviewSummary")

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_images(self, obj) -> list[str]:
        return [image.image_url for image in obj.images.all()]

    @extend_schema_field({"type": "object", "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}}})
    def get_map(self, obj) -> dict:
        return {"lat": float(obj.latitude), "lng": float(obj.longitude)}

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distanceFromUser(self, obj) -> float | None:
        distance = self.context.get("distance")
        return round(distance, 1) if distance is not None else None

    @extend_schema_field({"type": "object"})
    def get_reviewSummary(self, obj) -> dict:
        return {"avgRating": 0, "aiSatisfaction": None}


class PlacesErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField()

