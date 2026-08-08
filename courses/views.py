from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ApiResponse
from courses.serializers import (
    AIRecommendDataSerializer,
    AIRecommendRequestSerializer,
    CourseCompleteDataSerializer,
    CourseCompleteSerializer,
    CourseOptimizeDataSerializer,
    CourseOptimizeRequestSerializer,
    CoursesErrorResponseSerializer,
    CourseSaveDataSerializer,
    CourseShareDataSerializer,
    CourseStartDataSerializer,
)
from courses.services import (
    complete_course,
    optimize_route,
    request_ai_recommendation,
    save_course,
    share_course,
    start_course,
)


SaveResponse = inline_serializer(
    "CourseSaveSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": CourseSaveDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)
StartResponse = inline_serializer(
    "CourseStartSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": CourseStartDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)
CompleteResponse = inline_serializer(
    "CourseCompleteSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": CourseCompleteDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)
ShareResponse = inline_serializer(
    "CourseShareSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": CourseShareDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)
AIRecommendResponse = inline_serializer(
    "AIRecommendSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": AIRecommendDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)
CourseOptimizeResponse = inline_serializer(
    "CourseOptimizeSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": CourseOptimizeDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)


class CourseOptimizeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="코스 동선 최적화",
        operation_id="courses_optimize",
        tags=["Courses"],
        request=CourseOptimizeRequestSerializer,
        responses={
            200: CourseOptimizeResponse,
            400: CoursesErrorResponseSerializer,
            401: CoursesErrorResponseSerializer,
            404: CoursesErrorResponseSerializer,
            422: CoursesErrorResponseSerializer,
            500: CoursesErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = CourseOptimizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = optimize_route(
            place_ids=serializer.validated_data["placeIds"],
            transport=serializer.validated_data["transport"],
        )
        return ApiResponse(
            data={
                "orderedPlaces": result.ordered_place_ids,
                "segmentTimes": result.segment_times,
                "totalTime": result.total_time,
                "route": result.route,
            }
        )


class AIRecommendView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="AI 맞춤 코스 추천",
        operation_id="recommend_ai",
        tags=["Courses"],
        request=AIRecommendRequestSerializer,
        responses={
            200: AIRecommendResponse,
            400: CoursesErrorResponseSerializer,
            401: CoursesErrorResponseSerializer,
            422: CoursesErrorResponseSerializer,
            500: CoursesErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = AIRecommendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        course = request_ai_recommendation(
            user=request.user,
            mood=data["mood"],
            companion=data["companion"],
            transport=data["transport"],
            time_available=data["timeAvailable"],
            free_text=data["freeText"],
        )
        return ApiResponse(
            data={
                "courseId": course.id,
                "name": course.name,
                "reason": course.recommend_reason,
                "places": [
                    {"placeId": item.place_id, "order": item.order}
                    for item in course.places.order_by("order")
                ],
            }
        )


class CourseSaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="코스 저장",
        operation_id="courses_save",
        tags=["Courses"],
        request=None,
        responses={
            200: SaveResponse,
            401: CoursesErrorResponseSerializer,
            404: CoursesErrorResponseSerializer,
        },
    )
    def post(self, request, courseId):
        save_course(user=request.user, course_id=courseId)
        return ApiResponse(data={"saved": True})


class CourseStartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="코스 시작",
        operation_id="courses_start",
        tags=["Courses"],
        request=None,
        responses={
            200: StartResponse,
            401: CoursesErrorResponseSerializer,
            404: CoursesErrorResponseSerializer,
        },
    )
    def post(self, request, courseId):
        progress = start_course(user=request.user, course_id=courseId)
        return ApiResponse(data={"startedAt": progress.started_at})


class CourseCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="코스 완주 인증",
        operation_id="courses_complete",
        tags=["Courses"],
        request=CourseCompleteSerializer,
        responses={
            200: CompleteResponse,
            400: CoursesErrorResponseSerializer,
            401: CoursesErrorResponseSerializer,
            404: CoursesErrorResponseSerializer,
            422: CoursesErrorResponseSerializer,
        },
    )
    def post(self, request, courseId):
        serializer = CourseCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complete_course(
            user=request.user,
            course_id=courseId,
            check_in_locations=serializer.validated_data["checkInLocations"],
        )
        return ApiResponse(data={"completed": True, "cardId": None})


class CourseShareView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="코스 공유",
        operation_id="courses_share",
        tags=["Courses"],
        request=None,
        responses={
            200: ShareResponse,
            401: CoursesErrorResponseSerializer,
            404: CoursesErrorResponseSerializer,
        },
    )
    def post(self, request, courseId):
        share_url = share_course(course_id=courseId)
        return ApiResponse(data={"shareUrl": share_url})
