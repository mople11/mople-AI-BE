from math import asin, cos, radians, sin, sqrt

from django.db import transaction
from django.utils import timezone

from common.exceptions import ApiError, ErrorCode
from places.kakao_mobility import KakaoMobilityClient
from places.models import TouristSpot, TouristSpotImage
from places.tourapi import RawSpot, TourApiClient, TourApiError
from places.tourist_congestion import TouristCongestionClient


def _upsert_spot(raw: RawSpot, *, all_images=False):
    spot, _ = TouristSpot.objects.update_or_create(
        content_id=raw.content_id,
        defaults={
            "name": raw.name, "category": raw.category, "address": raw.address,
            "description": raw.description, "hours": raw.hours,
            "latitude": raw.latitude, "longitude": raw.longitude,
            "sigungu": raw.sigungu, "parking_available": raw.parking_available,
            "synced_at": timezone.now(),
        },
    )
    if all_images:
        spot.images.all().delete()
        TouristSpotImage.objects.bulk_create([
            TouristSpotImage(spot=spot, image_url=url, is_primary=index == 0, order=index)
            for index, url in enumerate(raw.image_urls)
        ])
    elif raw.image_urls:
        TouristSpotImage.objects.update_or_create(
            spot=spot, is_primary=True,
            defaults={"image_url": raw.image_urls[0], "order": 0},
        )
    return spot


def search_spots(*, keyword, category, region, sort):
    try:
        raw_spots = TourApiClient().search_spots(
            keyword=keyword, category=category, sigungu=region
        )
    except TourApiError as exc:
        raise ApiError(ErrorCode.EXTERNAL_API_ERROR) from exc
    with transaction.atomic():
        return [_upsert_spot(raw) for raw in raw_spots]


def get_spot_detail(*, place_id, user_lat=None, user_lng=None):
    try:
        cached = TouristSpot.objects.get(pk=place_id)
    except TouristSpot.DoesNotExist as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc
    try:
        raw = TourApiClient().get_spot_detail(content_id=cached.content_id)
    except TourApiError as exc:
        raise ApiError(ErrorCode.EXTERNAL_API_ERROR) from exc
    if raw is None:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND)
    with transaction.atomic():
        spot = _upsert_spot(raw, all_images=True)
    distance = None
    if user_lat is not None and user_lng is not None:
        distance = calculate_distance_km(user_lat, user_lng, spot.latitude, spot.longitude)
    return spot, distance


def get_congestion(*, place_id):
    try:
        spot = TouristSpot.objects.get(pk=place_id)
    except TouristSpot.DoesNotExist as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc
    return spot, TouristCongestionClient().get_forecast(
        spot_name=spot.name,
        sigungu=spot.sigungu,
    )


def get_traffic_congestion(*, origin, destination):
    return KakaoMobilityClient().get_traffic(origin=origin, destination=destination)


def calculate_distance_km(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(lambda value: radians(float(value)), (lat1, lng1, lat2, lng2))
    delta_lat, delta_lng = lat2 - lat1, lng2 - lng1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lng / 2) ** 2
    return 6371.0088 * 2 * asin(sqrt(value))
