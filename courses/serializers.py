from rest_framework import serializers

from common.exceptions import ApiError, ErrorCode


class AIRecommendRequestSerializer(serializers.Serializer):
    mood = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=50
    )
    companion = serializers.ChoiceField(
        choices=["혼자", "커플", "가족", "친구"],
        required=False,
        allow_blank=True,
        default="",
    )
    transport = serializers.ChoiceField(
        choices=["도보", "대중교통", "자차"],
        required=False,
        allow_blank=True,
        default="",
    )
    timeAvailable = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=50
    )
    freeText = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=500
    )

    def validate_mood(self, value):
        if not value.strip():
            raise ApiError(ErrorCode.MOOD_REQUIRED)
        return value


class AIRecommendPlaceDataSerializer(serializers.Serializer):
    placeId = serializers.IntegerField()
    order = serializers.IntegerField()


class AIRecommendDataSerializer(serializers.Serializer):
    courseId = serializers.IntegerField()
    name = serializers.CharField()
    reason = serializers.CharField()
    places = AIRecommendPlaceDataSerializer(many=True)


class CheckInLocationSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class CourseCompleteSerializer(serializers.Serializer):
    checkInLocations = CheckInLocationSerializer(many=True, allow_empty=False)


class CourseSaveDataSerializer(serializers.Serializer):
    saved = serializers.BooleanField()


class CourseStartDataSerializer(serializers.Serializer):
    startedAt = serializers.DateTimeField()


class CourseCompleteDataSerializer(serializers.Serializer):
    completed = serializers.BooleanField()
    cardId = serializers.IntegerField(allow_null=True)


class CourseShareDataSerializer(serializers.Serializer):
    shareUrl = serializers.URLField()


class CoursesErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField()
