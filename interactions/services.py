from django.db import IntegrityError, transaction

from common.exceptions import ApiError, ErrorCode
from interactions.models import Bookmark
from places.models import TouristSpot


def toggle_bookmark(*, place_id, user) -> bool:
    try:
        place = TouristSpot.objects.get(pk=place_id)
    except (TouristSpot.DoesNotExist, ValueError, TypeError) as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc

    deleted_count, _ = Bookmark.objects.filter(user=user, place=place).delete()
    if deleted_count:
        return False

    try:
        with transaction.atomic():
            Bookmark.objects.create(user=user, place=place)
    except IntegrityError:
        return True
    return True
