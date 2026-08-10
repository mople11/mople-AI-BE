from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ApiResponse
from mypage.serializers import (
    LikedPlaceSerializer,
    MypageErrorResponseSerializer,
    MyReviewSerializer,
    ProfileSummarySerializer,
    ProfileUpdateSerializer,
    SavedCourseSerializer,
)
from mypage.services import (
    get_liked_places,
    get_my_reviews,
    get_profile_summary,
    get_saved_courses,
    update_profile,
)


ProfileSummaryResponse = inline_serializer(
    "MypageProfileSummarySuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": ProfileSummarySerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)
ProfileUpdateResponse = inline_serializer(
    "MypageProfileUpdateSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "MypageProfileUpdateData",
            fields={"updated": serializers.BooleanField()},
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)
CoursesResponse = inline_serializer(
    "MypageCoursesSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "MypageCoursesData",
            fields={"courses": SavedCourseSerializer(many=True)},
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)
ReviewsResponse = inline_serializer(
    "MypageReviewsSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "MypageReviewsData",
            fields={"reviews": MyReviewSerializer(many=True)},
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)
LikesResponse = inline_serializer(
    "MypageLikesSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            "MypageLikesData",
            fields={"places": LikedPlaceSerializer(many=True)},
        ),
        "error": serializers.JSONField(allow_null=True),
    },
)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 프로필·활동 요약 조회",
        operation_id="mypage_me_retrieve",
        tags=["Mypage"],
        responses={200: ProfileSummaryResponse, 401: MypageErrorResponseSerializer},
    )
    def get(self, request):
        summary = get_profile_summary(user=request.user)
        return ApiResponse(data=ProfileSummarySerializer(summary).data)

    @extend_schema(
        summary="내 프로필 수정",
        operation_id="mypage_me_update",
        tags=["Mypage"],
        request=ProfileUpdateSerializer,
        responses={
            200: ProfileUpdateResponse,
            401: MypageErrorResponseSerializer,
            409: MypageErrorResponseSerializer,
            422: MypageErrorResponseSerializer,
        },
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_profile(user=request.user, **serializer.validated_data)
        return ApiResponse(data={"updated": True})


class MyCoursesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="저장한 코스 목록 조회",
        operation_id="mypage_courses_list",
        tags=["Mypage"],
        responses={200: CoursesResponse, 401: MypageErrorResponseSerializer},
    )
    def get(self, request):
        courses = get_saved_courses(user=request.user)
        return ApiResponse(data={"courses": SavedCourseSerializer(courses, many=True).data})


class MyReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 후기 목록 조회",
        operation_id="mypage_reviews_list",
        tags=["Mypage"],
        responses={200: ReviewsResponse, 401: MypageErrorResponseSerializer},
    )
    def get(self, request):
        reviews = get_my_reviews(user=request.user)
        return ApiResponse(data={"reviews": MyReviewSerializer(reviews, many=True).data})


class MyLikesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="찜한 장소 목록 조회",
        operation_id="mypage_likes_list",
        tags=["Mypage"],
        responses={200: LikesResponse, 401: MypageErrorResponseSerializer},
    )
    def get(self, request):
        places = get_liked_places(user=request.user)
        return ApiResponse(data={"places": LikedPlaceSerializer(places, many=True).data})
