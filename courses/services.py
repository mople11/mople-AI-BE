from django.conf import settings
from django.utils import timezone

from common.exceptions import ApiError, ErrorCode
from courses.models import Course, CoursePlace, CourseProgress
from places.services import calculate_distance_km


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
