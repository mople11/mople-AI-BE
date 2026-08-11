from rest_framework import serializers

from common.models import UserSettings


class NotificationsSerializer(serializers.Serializer):
    push = serializers.BooleanField(source="push_notification_enabled")
    goldenHour = serializers.BooleanField(source="golden_hour_notification_enabled")


class PermissionsSerializer(serializers.Serializer):
    location = serializers.BooleanField(source="location_permission_granted")


class UserSettingsSerializer(serializers.Serializer):
    notifications = NotificationsSerializer(source="*")
    language = serializers.ChoiceField(choices=UserSettings.Language.choices)
    permissions = PermissionsSerializer(source="*")


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError(
                    {field: ["허용되지 않는 필드입니다."] for field in unexpected}
                )
        return super().to_internal_value(data)


class NotificationsUpdateSerializer(StrictSerializer):
    push = serializers.BooleanField(
        source="push_notification_enabled", required=False
    )
    goldenHour = serializers.BooleanField(
        source="golden_hour_notification_enabled", required=False
    )


class PermissionsUpdateSerializer(StrictSerializer):
    location = serializers.BooleanField(
        source="location_permission_granted", required=False
    )


class UserSettingsUpdateSerializer(StrictSerializer):
    notifications = NotificationsUpdateSerializer(required=False)
    language = serializers.ChoiceField(
        choices=UserSettings.Language.choices, required=False
    )
    permissions = PermissionsUpdateSerializer(required=False)

    def validate(self, attrs):
        fields = {}
        fields.update(attrs.get("notifications", {}))
        fields.update(attrs.get("permissions", {}))
        if "language" in attrs:
            fields["language"] = attrs["language"]
        if not fields:
            raise serializers.ValidationError(
                "변경할 항목을 하나 이상 입력해야 합니다."
            )
        attrs["_flattened"] = fields
        return attrs


class PageQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    pageSize = serializers.IntegerField(
        required=False, min_value=1, max_value=50, default=20
    )


class PaginationMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    pageSize = serializers.IntegerField()
    totalCount = serializers.IntegerField()
    totalPages = serializers.IntegerField()
