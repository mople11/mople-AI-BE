from django.db import IntegrityError, transaction

from accounts.models import User
from common.exceptions import ApiError, ErrorCode
from courses.models import CourseProgress
from gamification.models import Stamp
from interactions.models import Bookmark
from reviews.models import Review


def get_profile_summary(*, user) -> dict:
    return {
        "profile": {
            "nickname": user.nickname,
            "profile_img": user.profile_img,
        },
        "stats": {
            "completedCourses": CourseProgress.objects.filter(
                user=user,
                status=CourseProgress.Status.COMPLETED,
            ).count(),
            "stamps": Stamp.objects.filter(user=user).count(),
            "reviews": Review.objects.filter(user=user).count(),
        },
    }


_UNSET = object()


def update_profile(*, user, nickname=_UNSET, profile_img=_UNSET) -> bool:
    if (
        nickname is not _UNSET
        and User.objects.filter(nickname=nickname)
        .exclude(pk=user.pk)
        .exists()
    ):
        raise ApiError(ErrorCode.NICKNAME_DUPLICATE)

    update_fields = []
    if nickname is not _UNSET:
        user.nickname = nickname
        update_fields.append("nickname")
    if profile_img is not _UNSET:
        user.profile_img = profile_img or None
        update_fields.append("profile_img")

    if not update_fields:
        return True

    try:
        with transaction.atomic():
            user.save(update_fields=update_fields)
    except IntegrityError as exc:
        raise ApiError(ErrorCode.NICKNAME_DUPLICATE) from exc
    return True


def get_saved_courses(*, user):
    return (
        CourseProgress.objects.filter(
            user=user,
            status__in=[
                CourseProgress.Status.SAVED,
                CourseProgress.Status.IN_PROGRESS,
                CourseProgress.Status.COMPLETED,
            ],
        )
        .select_related("course")
        .order_by("-updated_at")
    )


def get_my_reviews(*, user):
    return Review.objects.filter(user=user).select_related("place").order_by("-id")


def get_liked_places(*, user):
    return (
        Bookmark.objects.filter(user=user)
        .select_related("place")
        .order_by("-created_at")
    )
