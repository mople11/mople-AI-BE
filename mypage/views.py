from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from accounts.serializers import WithdrawSerializer
from accounts.services import withdraw_user
from common.pagination import paginate_queryset
from common.response import ApiResponse
from common.serializers import PaginationMetaSerializer
from mypage.serializers import (
    LikedPlaceSerializer,
    MypageErrorResponseSerializer,
    MypageListQuerySerializer,
    MyReviewSerializer,
    ProfileSummarySerializer,
    ProfileUpdateSerializer,
    SavedCourseSerializer,
    WithdrawalSuccessResponseSerializer,
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
            fields={
                "courses": SavedCourseSerializer(many=True),
                "pagination": PaginationMetaSerializer(),
            },
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
            fields={
                "reviews": MyReviewSerializer(many=True),
                "pagination": PaginationMetaSerializer(),
            },
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
            fields={
                "places": LikedPlaceSerializer(many=True),
                "pagination": PaginationMetaSerializer(),
            },
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

    @extend_schema(
        summary="회원탈퇴",
        description=(
            "일반 계정은 현재 비밀번호를 확인하며, 소셜 계정은 비밀번호 없이 "
            "탈퇴합니다. 계정은 비활성화하고 개인정보를 익명화합니다."
        ),
        operation_id="mypage_me_destroy",
        tags=["Mypage"],
        request=WithdrawSerializer,
        responses={
            200: OpenApiResponse(
                response=WithdrawalSuccessResponseSerializer,
                description="회원탈퇴 성공",
                examples=[
                    OpenApiExample(
                        "회원탈퇴 성공",
                        value={"success": True, "data": None, "error": None},
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                response=MypageErrorResponseSerializer,
                description="일반 계정의 현재 비밀번호 불일치 또는 누락",
                examples=[
                    OpenApiExample(
                        "비밀번호 불일치",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "PASSWORD_MISMATCH",
                                "message": "비밀번호가 일치하지 않습니다.",
                            },
                        },
                        response_only=True,
                    )
                ],
            ),
            401: OpenApiResponse(
                response=MypageErrorResponseSerializer,
                description="access token 누락 또는 인증 실패",
                examples=[
                    OpenApiExample(
                        "인증 실패",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "AUTH_401",
                                "message": "인증이 필요합니다.",
                            },
                        },
                        response_only=True,
                    )
                ],
            ),
            409: OpenApiResponse(
                response=MypageErrorResponseSerializer,
                description="이미 탈퇴 처리된 계정으로 재요청됨(동시 탈퇴 요청 등)",
                examples=[
                    OpenApiExample(
                        "이미 탈퇴한 계정",
                        value={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "ACCOUNT_ALREADY_WITHDRAWN",
                                "message": "이미 탈퇴한 계정입니다.",
                            },
                        },
                        response_only=True,
                    )
                ],
            ),
            422: MypageErrorResponseSerializer,
        },
    )
    def delete(self, request):
        serializer = WithdrawSerializer(
            data=request.data,
            context={"user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        withdraw_user(
            user=request.user,
            password=serializer.validated_data.get("password"),
        )
        return ApiResponse()


class MyCoursesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="저장한 코스 목록 조회",
        operation_id="mypage_courses_list",
        tags=["Mypage"],
        parameters=[MypageListQuerySerializer],
        responses={
            200: CoursesResponse,
            401: MypageErrorResponseSerializer,
            422: MypageErrorResponseSerializer,
        },
    )
    def get(self, request):
        query = MypageListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        courses = get_saved_courses(user=request.user)
        items, pagination = paginate_queryset(
            courses, page=values["page"], page_size=values["pageSize"]
        )
        return ApiResponse(data={
            "courses": SavedCourseSerializer(items, many=True).data,
            "pagination": pagination,
        })


class MyReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 후기 목록 조회",
        operation_id="mypage_reviews_list",
        tags=["Mypage"],
        parameters=[MypageListQuerySerializer],
        responses={
            200: ReviewsResponse,
            401: MypageErrorResponseSerializer,
            422: MypageErrorResponseSerializer,
        },
    )
    def get(self, request):
        query = MypageListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        reviews = get_my_reviews(user=request.user)
        items, pagination = paginate_queryset(
            reviews, page=values["page"], page_size=values["pageSize"]
        )
        return ApiResponse(data={
            "reviews": MyReviewSerializer(items, many=True).data,
            "pagination": pagination,
        })


class MyLikesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="찜한 장소 목록 조회",
        operation_id="mypage_likes_list",
        tags=["Mypage"],
        parameters=[MypageListQuerySerializer],
        responses={
            200: LikesResponse,
            401: MypageErrorResponseSerializer,
            422: MypageErrorResponseSerializer,
        },
    )
    def get(self, request):
        query = MypageListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        places = get_liked_places(user=request.user)
        items, pagination = paginate_queryset(
            places, page=values["page"], page_size=values["pageSize"]
        )
        return ApiResponse(data={
            "places": LikedPlaceSerializer(items, many=True).data,
            "pagination": pagination,
        })
