from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from common.response import ApiResponse
from reviews.serializers import (
    ReviewCreateSerializer, ReviewListItemSerializer, ReviewListQuerySerializer,
    ReviewReportSerializer, ReviewSummaryQuerySerializer, ReviewsErrorResponseSerializer,
)
from reviews.services import (
    create_report,
    create_review,
    get_review_summary,
    list_reviews,
    toggle_review_helpful,
)


CreateResponse = inline_serializer("ReviewCreateSuccess", fields={
    "success": serializers.BooleanField(),
    "data": inline_serializer("ReviewCreateData", fields={"reviewId": serializers.CharField()}),
    "error": serializers.JSONField(allow_null=True),
})
ListResponse = inline_serializer("ReviewListSuccess", fields={
    "success": serializers.BooleanField(),
    "data": inline_serializer("ReviewListData", fields={"reviews": ReviewListItemSerializer(many=True)}),
    "error": serializers.JSONField(allow_null=True),
})
HelpfulResponse = inline_serializer("ReviewHelpfulSuccess", fields={
    "success": serializers.BooleanField(),
    "data": inline_serializer("ReviewHelpfulData", fields={"count": serializers.IntegerField()}),
    "error": serializers.JSONField(allow_null=True),
})
ReportResponse = inline_serializer("ReviewReportSuccess", fields={
    "success": serializers.BooleanField(),
    "data": inline_serializer("ReviewReportData", fields={"reported": serializers.BooleanField()}),
    "error": serializers.JSONField(allow_null=True),
})
SummaryResponse = inline_serializer("ReviewSummarySuccess", fields={
    "success": serializers.BooleanField(),
    "data": inline_serializer("ReviewSummaryData", fields={
        "score": serializers.IntegerField(),
        "keywords": inline_serializer("ReviewSummaryKeywords", fields={
            "positive": serializers.ListField(child=serializers.CharField()),
            "negative": serializers.ListField(child=serializers.CharField()),
        }),
    }),
    "error": serializers.JSONField(allow_null=True),
})


class ReviewCollectionView(APIView):
    def get_permissions(self):
        classes = [AllowAny] if self.request.method == "GET" else [IsAuthenticated]
        return [permission() for permission in classes]

    @extend_schema(
        summary="후기 작성", operation_id="reviews_create", tags=["Reviews"], request=ReviewCreateSerializer,
        responses={200: CreateResponse, 400: ReviewsErrorResponseSerializer, 404: ReviewsErrorResponseSerializer, 422: ReviewsErrorResponseSerializer},
    )
    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        review = create_review(
            user=request.user, target_id=values["targetId"], rating=values.get("rating"),
            text=values["text"], photos=values["photos"], visit_date=values["visitDate"],
            visit_weather=values["visitWeather"],
        )
        return ApiResponse(data={"reviewId": str(review.id)})

    @extend_schema(
        summary="후기 목록 조회", operation_id="reviews_list", tags=["Reviews"], auth=[],
        parameters=[ReviewListQuerySerializer], responses={200: ListResponse, 422: ReviewsErrorResponseSerializer},
    )
    def get(self, request):
        serializer = ReviewListQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        reviews = list_reviews(target_id=values["targetId"], sort=values["sort"])
        return ApiResponse(data={"reviews": ReviewListItemSerializer(reviews, many=True).data})


class ReviewSummaryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="AI 만족도·키워드 요약", operation_id="reviews_summary", tags=["Reviews"],
        auth=[], parameters=[ReviewSummaryQuerySerializer], responses={200: SummaryResponse},
    )
    def get(self, request):
        serializer = ReviewSummaryQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = get_review_summary(target_id=serializer.validated_data["targetId"])
        return ApiResponse(data=data)


class ReviewHelpfulView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="후기 도움돼요", operation_id="reviews_helpful", tags=["Reviews"], request=None,
        responses={200: HelpfulResponse, 404: ReviewsErrorResponseSerializer},
    )
    def post(self, request, reviewId):
        count = toggle_review_helpful(review_id=reviewId, user=request.user)
        return ApiResponse(data={"count": count})


class ReviewReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="후기 신고", operation_id="reviews_report", tags=["Reviews"], request=ReviewReportSerializer,
        responses={200: ReportResponse, 404: ReviewsErrorResponseSerializer, 422: ReviewsErrorResponseSerializer},
    )
    def post(self, request, reviewId):
        serializer = ReviewReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        create_report(review_id=reviewId, user=request.user, reason=serializer.validated_data["reason"])
        return ApiResponse(data={"reported": True})
