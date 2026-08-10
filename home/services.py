from common.exceptions import ApiError, ErrorCode
from courses.models import Course, CoursePlace
from django.db.models import Prefetch
from gamification.models import HiddenCourse, UserHiddenCourseUnlock
from home.kma import KmaClient
from places.models import TouristSpotImage


RECOMMENDED_COURSES_LIMIT = 5


def get_current_weather(*, lat: float, lng: float) -> dict:
    weather = KmaClient().get_current_weather(lat=lat, lng=lng)
    if weather is None:
        raise ApiError(ErrorCode.WEATHER_FETCH_FAILED)
    return {
        "weatherType": weather.weather_type,
        "temp": weather.temp,
        "icon": weather.icon,
    }


def get_home_data(*, lat: float, lng: float, user) -> dict:
    weather = get_current_weather(lat=lat, lng=lng)
    recommended_courses = (
        Course.objects.filter(status=Course.Status.SAVED)
        .order_by("-id")
        .prefetch_related(
            Prefetch(
                "places",
                queryset=CoursePlace.objects.select_related("place")
                .prefetch_related(
                    Prefetch(
                        "place__images",
                        queryset=TouristSpotImage.objects.filter(is_primary=True),
                        to_attr="primary_images",
                    )
                )
                .order_by("order"),
                to_attr="home_places",
            )
        )[:RECOMMENDED_COURSES_LIMIT]
    )
    return {
        "weather": {
            "type": weather["weatherType"],
            "temp": weather["temp"],
            "icon": weather["icon"],
        },
        "recommendedCourses": list(recommended_courses),
        "unlockBanner": {"available": _has_locked_hidden_course(user=user)},
    }


def _has_locked_hidden_course(*, user) -> bool:
    if user.is_authenticated:
        unlocked_ids = UserHiddenCourseUnlock.objects.filter(
            user=user
        ).values_list("hidden_course_id", flat=True)
        return HiddenCourse.objects.exclude(pk__in=unlocked_ids).exists()
    return HiddenCourse.objects.exists()
