from common.exceptions import ApiError, ErrorCode
from gamification.kakao_local import KakaoLocalClient
from gamification.models import Stamp


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
