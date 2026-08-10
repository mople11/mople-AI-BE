from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ApiResponse
from common.serializers import UserSettingsSerializer, UserSettingsUpdateSerializer
from common.services import get_or_create_settings, update_settings


SettingsResponse = inline_serializer(
    "UserSettingsSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": UserSettingsSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)


class UserSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="설정 조회",
        operation_id="settings_retrieve",
        tags=["Common"],
        responses={200: SettingsResponse},
    )
    def get(self, request):
        settings_obj = get_or_create_settings(user=request.user)
        return ApiResponse(data=UserSettingsSerializer(settings_obj).data)

    @extend_schema(
        summary="설정 변경",
        operation_id="settings_update",
        tags=["Common"],
        request=UserSettingsUpdateSerializer,
        responses={200: SettingsResponse},
    )
    def patch(self, request):
        serializer = UserSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_settings(user=request.user, **serializer.validated_data["_flattened"])
        return ApiResponse(data={"updated": True})
