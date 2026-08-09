from django.conf import settings

from common.exceptions import ApiError, ErrorCode
from courses.models import CourseProgress
from gamification.kakao_local import KakaoLocalClient
from gamification.models import (
    CompletionCard,
    HiddenCourse,
    Stamp,
    UserHiddenCourseUnlock,
)


TOTAL_STAMP_COUNT = 22


def checkin(*, lat: float, lng: float, user) -> dict:
    city_code = KakaoLocalClient().get_city_code(lat=lat, lng=lng)
    if not city_code:
        raise ApiError(ErrorCode.OUT_OF_REGION)

    _, created = Stamp.objects.get_or_create(user=user, city_code=city_code)
    return {"stampAcquired": created, "cityCode": city_code}


def get_stampbook_status(*, user) -> dict:
    collected = list(
        Stamp.objects.filter(user=user)
        .order_by("acquired_at", "pk")
        .values_list("city_code", flat=True)
    )
    progress = round(len(collected) / TOTAL_STAMP_COUNT * 100)
    return {
        "collected": collected,
        "totalCount": TOTAL_STAMP_COUNT,
        "progress": progress,
    }


def get_unlocked_courses(*, user) -> dict:
    unlocked_ids = set(
        UserHiddenCourseUnlock.objects.filter(user=user).values_list(
            "hidden_course_id", flat=True
        )
    )
    unlocked_courses = []
    locked_courses = []
    for hidden_course in HiddenCourse.objects.all():
        if hidden_course.id in unlocked_ids:
            unlocked_courses.append(
                {
                    "courseId": hidden_course.course_id,
                    "rarity": hidden_course.rarity,
                }
            )
        else:
            locked_courses.append(
                {
                    "courseId": hidden_course.course_id,
                    "unlockCondition": hidden_course.unlock_condition,
                }
            )
    return {
        "unlockedCourses": unlocked_courses,
        "lockedCourses": locked_courses,
    }


def create_completion_card(*, user, course_id, user_photo) -> CompletionCard:
    progress = CourseProgress.objects.filter(
        user=user, course_id=course_id
    ).first()
    if not progress or progress.status != CourseProgress.Status.COMPLETED:
        raise ApiError(ErrorCode.COURSE_NOT_COMPLETED)

    card, _ = CompletionCard.objects.update_or_create(
        user=user,
        course_id=course_id,
        defaults={"user_photo": user_photo, "card_image_url": user_photo},
    )
    return card


def share_completion_card(*, user, card_id) -> str:
    try:
        card = CompletionCard.objects.get(pk=card_id, user=user)
    except CompletionCard.DoesNotExist:
        raise ApiError(ErrorCode.COMMON_404)
    return f"{settings.CARD_SHARE_BASE_URL}/{card.id}"
