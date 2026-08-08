import itertools
from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from common.exceptions import ApiError, ErrorCode
from courses.ai_recommend import AIRecommendClient, AIRecommendError
from courses.models import Course, CoursePlace, CourseProgress
from places.kakao_mobility import KakaoMobilityClient
from places.models import TouristSpot
from places.services import calculate_distance_km


@dataclass(frozen=True)
class OptimizedRoute:
    ordered_place_ids: list[str]
    segment_times: list[int]
    total_time: int
    route: dict


def optimize_route(*, place_ids: list[str], transport: str) -> OptimizedRoute:
    if len(place_ids) < 2:
        raise ApiError(ErrorCode.MIN_PLACE_REQUIRED)

    try:
        pks = [int(place_id) for place_id in place_ids]
    except ValueError as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc

    spots_by_pk = {
        spot.pk: spot
        for spot in TouristSpot.objects.filter(pk__in=pks)
    }
    try:
        coords = [
            (spots_by_pk[pk].latitude, spots_by_pk[pk].longitude)
            for pk in pks
        ]
    except KeyError as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc

    duration_matrix = _build_duration_matrix(coords)
    if duration_matrix is None:
        raise ApiError(ErrorCode.ROUTE_CALC_FAILED)

    best_order = _shortest_path_order(duration_matrix)
    segment_times = [
        duration_matrix[best_order[i]][best_order[i + 1]]
        for i in range(len(best_order) - 1)
    ]
    return OptimizedRoute(
        ordered_place_ids=[place_ids[i] for i in best_order],
        segment_times=segment_times,
        total_time=sum(segment_times),
        route={},
    )


def _build_duration_matrix(coords: list[tuple]) -> list[list[int]] | None:
    client = KakaoMobilityClient()
    n = len(coords)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            traffic = client.get_traffic(origin=coords[i], destination=coords[j])
            if traffic is None:
                return None
            matrix[i][j] = traffic.eta_min
    return matrix


def _shortest_path_order(matrix: list[list[int]]) -> list[int]:
    n = len(matrix)
    best_order, best_total = None, None
    for perm in itertools.permutations(range(n)):
        total = sum(matrix[perm[i]][perm[i + 1]] for i in range(n - 1))
        if best_total is None or total < best_total:
            best_order, best_total = perm, total
    return list(best_order)


def request_ai_recommendation(
    *, user, mood, companion, transport, time_available, free_text
) -> Course:
    try:
        recommendation = AIRecommendClient().recommend(
            mood=mood,
            companion=companion,
            transport=transport,
            time_available=time_available,
            free_text=free_text,
        )
    except AIRecommendError as exc:
        raise ApiError(ErrorCode.AI_RECOMMEND_FAILED) from exc

    if not recommendation.places:
        raise ApiError(ErrorCode.AI_RECOMMEND_FAILED)

    content_ids = [item.content_id for item in recommendation.places]
    spots_by_content_id = {
        spot.content_id: spot
        for spot in TouristSpot.objects.filter(content_id__in=content_ids)
    }
    resolved = []
    for item in recommendation.places:
        spot = spots_by_content_id.get(item.content_id)
        if spot is None:
            raise ApiError(ErrorCode.AI_RECOMMEND_FAILED)
        resolved.append((spot, item.order))

    try:
        with transaction.atomic():
            course = Course.objects.create(
                owner=user,
                name=recommendation.name,
                recommend_reason=recommendation.reason,
                mood=mood,
                companion_type=companion,
                transport_type=transport,
                time_available=time_available,
                free_text=free_text,
                status=Course.Status.TEMP,
            )
            CoursePlace.objects.bulk_create(
                [
                    CoursePlace(course=course, place=spot, order=order)
                    for spot, order in resolved
                ]
            )
    except IntegrityError as exc:
        raise ApiError(ErrorCode.AI_RECOMMEND_FAILED) from exc
    return course


def _get_course(course_id) -> Course:
    try:
        return Course.objects.get(pk=course_id)
    except Course.DoesNotExist as exc:
        raise ApiError(ErrorCode.COURSE_NOT_FOUND) from exc


def save_course(*, user, course_id) -> Course:
    course = _get_course(course_id)
    course.status = Course.Status.SAVED
    course.save(update_fields=["status"])
    CourseProgress.objects.update_or_create(
        user=user,
        course=course,
        defaults={"status": CourseProgress.Status.SAVED},
    )
    return course


def start_course(*, user, course_id) -> CourseProgress:
    course = _get_course(course_id)
    progress, _ = CourseProgress.objects.update_or_create(
        user=user,
        course=course,
        defaults={
            "status": CourseProgress.Status.IN_PROGRESS,
            "started_at": timezone.now(),
        },
    )
    return progress


def complete_course(*, user, course_id, check_in_locations) -> CourseProgress:
    course = _get_course(course_id)
    course_places = list(
        CoursePlace.objects.filter(course=course)
        .select_related("place")
        .order_by("order")
    )

    if len(check_in_locations) != len(course_places):
        raise ApiError(ErrorCode.LOCATION_MISMATCH)

    for location, course_place in zip(check_in_locations, course_places):
        distance_m = calculate_distance_km(
            location["lat"],
            location["lng"],
            course_place.place.latitude,
            course_place.place.longitude,
        ) * 1000
        if distance_m > settings.COURSE_CHECKIN_RADIUS_M:
            raise ApiError(ErrorCode.LOCATION_MISMATCH)

    progress, _ = CourseProgress.objects.update_or_create(
        user=user,
        course=course,
        defaults={
            "status": CourseProgress.Status.COMPLETED,
            "completed_at": timezone.now(),
        },
    )
    return progress


def share_course(*, course_id) -> str:
    course = _get_course(course_id)
    return f"{settings.COURSE_SHARE_BASE_URL}/{course.id}"
