from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response import ApiResponse
from home.serializers import (
    HomeDataSerializer,
    HomeErrorResponseSerializer,
    LocationQuerySerializer,
    WeatherDataSerializer,
)
from home.services import get_current_weather, get_home_data


WeatherResponse = inline_serializer(
    "WeatherCurrentSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": WeatherDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)
HomeResponse = inline_serializer(
    "HomeDataSuccess",
    fields={
        "success": serializers.BooleanField(),
        "data": HomeDataSerializer(),
        "error": serializers.JSONField(allow_null=True),
    },
)


class WeatherCurrentView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="현재 날씨 조회",
        operation_id="weather_current",
        tags=["Home"],
        parameters=[LocationQuerySerializer],
        responses={
            200: WeatherResponse,
            422: HomeErrorResponseSerializer,
            502: HomeErrorResponseSerializer,
        },
    )
    def get(self, request):
        query = LocationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = get_current_weather(**query.validated_data)
        return ApiResponse(data=WeatherDataSerializer(data).data)


class HomeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="메인 홈 데이터 조회",
        operation_id="home_data",
        tags=["Home"],
        parameters=[LocationQuerySerializer],
        responses={
            200: HomeResponse,
            422: HomeErrorResponseSerializer,
            502: HomeErrorResponseSerializer,
        },
    )
    def get(self, request):
        query = LocationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = get_home_data(user=request.user, **query.validated_data)
        return ApiResponse(data=HomeDataSerializer(data).data)
