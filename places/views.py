from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response import ApiResponse
from places.serializers import (
    PlacesErrorResponseSerializer, SpotDetailQuerySerializer, SpotDetailSerializer,
    SpotSearchQuerySerializer, SpotSearchResultSerializer, TrafficQuerySerializer,
)
from places.services import (
    get_congestion, get_spot_detail, get_traffic_congestion, search_spots,
)


SearchResponse = inline_serializer("SpotSearchSuccess", fields={
    "success": serializers.BooleanField(),
    "data": inline_serializer("SpotSearchData", fields={"results": SpotSearchResultSerializer(many=True)}),
    "error": serializers.JSONField(allow_null=True),
})
DetailResponse = inline_serializer("SpotDetailSuccess", fields={
    "success": serializers.BooleanField(), "data": SpotDetailSerializer(),
    "error": serializers.JSONField(allow_null=True),
})
CongestionResponse = inline_serializer("CongestionSuccess", fields={
    "success": serializers.BooleanField(), "data": serializers.JSONField(),
    "error": serializers.JSONField(allow_null=True),
})
TrafficResponse = inline_serializer("TrafficSuccess", fields={
    "success": serializers.BooleanField(), "data": serializers.JSONField(),
    "error": serializers.JSONField(allow_null=True),
})


class SpotSearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="통합 검색", operation_id="places_search", tags=["Places"], auth=[],
        parameters=[SpotSearchQuerySerializer],
        responses={200: SearchResponse, 422: PlacesErrorResponseSerializer, 502: PlacesErrorResponseSerializer},
    )
    def get(self, request):
        query = SpotSearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        spots = search_spots(
            keyword=values.get("keyword"), category=values.get("category"),
            region=values.get("region"), sort=values.get("sort"),
        )
        return ApiResponse(data={"results": SpotSearchResultSerializer(spots, many=True).data})


class SpotDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="장소 상세", operation_id="places_detail", tags=["Places"], auth=[],
        parameters=[SpotDetailQuerySerializer],
        responses={200: DetailResponse, 404: PlacesErrorResponseSerializer, 422: PlacesErrorResponseSerializer, 502: PlacesErrorResponseSerializer},
    )
    def get(self, request, place_id):
        query = SpotDetailQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        spot, distance = get_spot_detail(
            place_id=place_id, user_lat=values.get("latitude"), user_lng=values.get("longitude")
        )
        return ApiResponse(data=SpotDetailSerializer(spot, context={"distance": distance}).data)


class SpotCongestionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="관광지 혼잡도", operation_id="places_congestion", tags=["Places"], auth=[],
        responses={200: CongestionResponse, 404: PlacesErrorResponseSerializer},
    )
    def get(self, request, place_id):
        spot, congestion = get_congestion(place_id=place_id)
        if congestion is None:
            return ApiResponse(data={})
        return ApiResponse(data={
            "level": congestion.level,
            "parkingAvailable": spot.parking_available,
            "hourlyGraph": congestion.hourly_graph,
            "recommendedTime": congestion.recommended_time,
        })


class TrafficCongestionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="실시간 교통 혼잡 안내", operation_id="traffic_congestion", tags=["Places"], auth=[],
        parameters=[TrafficQuerySerializer],
        responses={200: TrafficResponse, 422: PlacesErrorResponseSerializer},
    )
    def get(self, request):
        query = TrafficQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        traffic = get_traffic_congestion(
            origin=(values["origin"]["lat"], values["origin"]["lng"]),
            destination=(values["destination"]["lat"], values["destination"]["lng"]),
        )
        if traffic is None:
            return ApiResponse(data={})
        return ApiResponse(data={
            "segments": traffic.segments, "etaMin": traffic.eta_min,
            "altRoute": traffic.alt_route,
        })
