from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from common.exceptions import ApiError, ErrorCode
from courses.ai_recommend import AIRecommendClient, AIRecommendError
from courses.models import Course, CoursePlace, CourseProgress
from places.models import TouristSpot
from places.services import calculate_distance_km


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
