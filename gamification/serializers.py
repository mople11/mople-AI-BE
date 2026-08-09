from rest_framework import serializers


class StampCheckinSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class GamificationErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField()
