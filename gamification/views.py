from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ApiResponse
from gamification.models import CompletionCard
from gamification.serializers import (
    CompletionCardCreateSerializer,
    GamificationErrorResponseSerializer,
    HiddenCourseUnlockedQuerySerializer,
    StampCheckinSerializer,
)
from gamification.services import (
    checkin,
    create_completion_card,
    get_stampbook_status,
    get_unlocked_courses,
    share_completion_card,
)


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
HiddenCoursesResponse = inline_serializer(
    "HiddenCoursesSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "HiddenCoursesData",
            fields={
                "unlockedCourses": serializers.ListField(
                    child=inline_serializer(
                        "UnlockedCourse",
                        fields={
                            "courseId": serializers.IntegerField(),
                            "rarity": serializers.CharField(),
                        },
                    )
                ),
                "lockedCourses": serializers.ListField(
                    child=inline_serializer(
                        "LockedCourse",
                        fields={
                            "courseId": serializers.IntegerField(),
                            "unlockCondition": serializers.CharField(),
                        },
                    )
                ),
            },
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)
CompletionCardCreateResponse = inline_serializer(
    "CompletionCardCreateSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "CompletionCardCreateData",
            fields={
                "cardId": serializers.IntegerField(),
                "cardImageUrl": serializers.URLField(),
            },
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)
CompletionCardListResponse = inline_serializer(
    "CompletionCardListSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "CompletionCardListData",
            fields={
                "cards": serializers.ListField(
                    child=inline_serializer(
                        "CompletionCardItem",
                        fields={
                            "cardId": serializers.IntegerField(),
                            "courseName": serializers.CharField(),
                            "date": serializers.DateTimeField(),
                            "imageUrl": serializers.URLField(),
                        },
                    )
                )
            },
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)
CompletionCardShareResponse = inline_serializer(
    "CompletionCardShareSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "CompletionCardShareData",
            fields={"shareUrl": serializers.URLField()},
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


class HiddenCourseUnlockedView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="숨겨진 여행지 목록 조회",
        operation_id="gamification_courses_unlocked",
        tags=["Gamification"],
        parameters=[HiddenCourseUnlockedQuerySerializer],
        responses={
            200: HiddenCoursesResponse,
            422: GamificationErrorResponseSerializer,
        },
    )
    def get(self, request):
        serializer = HiddenCourseUnlockedQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return ApiResponse(data=get_unlocked_courses(user=request.user))


class CompletionCardCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="완주 카드 생성",
        operation_id="gamification_cards_completion",
        tags=["Gamification"],
        request=CompletionCardCreateSerializer,
        responses={
            200: CompletionCardCreateResponse,
            400: GamificationErrorResponseSerializer,
            422: GamificationErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = CompletionCardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        card = create_completion_card(
            user=request.user,
            course_id=values["courseId"],
            user_photo=values["userPhoto"],
        )
        return ApiResponse(
            data={"cardId": card.id, "cardImageUrl": card.card_image_url}
        )


class CompletionCardListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="완주 카드 컬렉션 조회",
        operation_id="gamification_cards_list",
        tags=["Gamification"],
        responses={200: CompletionCardListResponse},
    )
    def get(self, request):
        cards = (
            CompletionCard.objects.filter(user=request.user)
            .select_related("course")
            .order_by("-id")
        )
        data = {
            "cards": [
                {
                    "cardId": card.id,
                    "courseName": card.course.name,
                    "date": card.created_at,
                    "imageUrl": card.card_image_url,
                }
                for card in cards
            ]
        }
        return ApiResponse(data=data)


class CompletionCardShareView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="완주 카드 공유",
        operation_id="gamification_cards_share",
        tags=["Gamification"],
        request=None,
        responses={
            200: CompletionCardShareResponse,
            404: GamificationErrorResponseSerializer,
        },
    )
    def post(self, request, cardId):
        share_url = share_completion_card(user=request.user, card_id=cardId)
        return ApiResponse(data={"shareUrl": share_url})
