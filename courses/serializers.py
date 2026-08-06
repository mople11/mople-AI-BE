from rest_framework import serializers


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
