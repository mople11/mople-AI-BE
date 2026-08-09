from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ApiResponse
from gamification.serializers import (
    GamificationErrorResponseSerializer,
    StampCheckinSerializer,
)
from gamification.services import checkin, get_stampbook_status


CheckinResponse = inline_serializer(
    "StampCheckinSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "StampCheckinData",
            fields={
                "stampAcquired": serializers.BooleanField(),
                "cityCode": serializers.CharField(),
            },
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)
StampbookResponse = inline_serializer(
    "StampbookStatusSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "StampbookStatusData",
            fields={
                "collected": serializers.ListField(child=serializers.CharField()),
                "totalCount": serializers.IntegerField(),
                "progress": serializers.IntegerField(),
            },
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)


class StampCheckinView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="위치 체크인(스탬프 획득)",
        operation_id="gamification_stamps_checkin",
        tags=["Gamification"],
        request=StampCheckinSerializer,
        responses={
            200: CheckinResponse,
            400: GamificationErrorResponseSerializer,
            422: GamificationErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = StampCheckinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        data = checkin(lat=values["lat"], lng=values["lng"], user=request.user)
        return ApiResponse(data=data)


class StampbookView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="스탬프북 현황 조회",
        operation_id="gamification_stamps_status",
        tags=["Gamification"],
        responses={200: StampbookResponse},
    )
    def get(self, request):
        data = get_stampbook_status(user=request.user)
        return ApiResponse(data=data)
