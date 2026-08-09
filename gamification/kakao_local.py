import logging

import requests
from django.conf import settings

from places.tourist_congestion import SIGUNGU_NAME_TO_CODE


logger = logging.getLogger(__name__)

KAKAO_LOCAL_BASE_URL = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
KAKAO_LOCAL_TIMEOUT_SEC = 5
JEOLLANAM_DO_NAME = "전라남도"


class KakaoLocalClient:
    def __init__(self):
        self.api_key = settings.KAKAO_REST_API_KEY
        self.timeout = KAKAO_LOCAL_TIMEOUT_SEC

    def get_city_code(self, *, lat: float, lng: float) -> str | None:
        try:
            response = requests.get(
                KAKAO_LOCAL_BASE_URL,
                headers={"Authorization": f"KakaoAK {self.api_key}"},
                params={"x": lng, "y": lat},
                timeout=self.timeout,
            )
            response.raise_for_status()
            documents = response.json().get("documents", [])
        except (
            requests.RequestException,
            AttributeError,
            ValueError,
            KeyError,
            TypeError,
        ):
            logger.warning(
                "Kakao Local API call failed lat=%s lng=%s",
                lat,
                lng,
                exc_info=True,
            )
            return None

        legal_docs = [doc for doc in documents if doc.get("region_type") == "B"]
        if not legal_docs:
            return None

        region = legal_docs[0]
        if region.get("region_1depth_name") != JEOLLANAM_DO_NAME:
            return None
        return SIGUNGU_NAME_TO_CODE.get(region.get("region_2depth_name"))
