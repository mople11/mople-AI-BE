from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ApiResponse
from interactions.serializers import BookmarkErrorResponseSerializer
from interactions.services import toggle_bookmark


BookmarkResponse = inline_serializer(
    "BookmarkSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "BookmarkData", fields={"liked": serializers.BooleanField()}
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)


class BookmarkToggleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="장소 찜하기 토글",
        operation_id="interactions_bookmark_toggle",
        tags=["Interactions"],
        request=None,
        responses={200: BookmarkResponse, 404: BookmarkErrorResponseSerializer},
    )
    def post(self, request, placeId):
        liked = toggle_bookmark(place_id=placeId, user=request.user)
        return ApiResponse(data={"liked": liked})
