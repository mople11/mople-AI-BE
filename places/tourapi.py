from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


JEOLLANAM_DO_AREA_CODE = "38"
CATEGORY_TO_CONTENT_TYPE = {
    "관광지": "12",
    "맛집": "39",
    "숙박": "32",
    "축제": "15",
}
CONTENT_TYPE_TO_CATEGORY = {
    value: key for key, value in {
        "ATTRACTION": "12", "RESTAURANT": "39", "LODGING": "32", "FESTIVAL": "15"
    }.items()
}
SIGUNGU_CODE_TO_NAME = {
    "1": "강진군", "2": "고흥군", "3": "곡성군", "4": "광양시",
    "5": "구례군", "6": "나주시", "7": "담양군", "8": "목포시",
    "9": "무안군", "10": "보성군", "11": "순천시", "12": "신안군",
    "13": "여수시", "16": "영광군", "17": "영암군", "18": "완도군",
    "19": "장성군", "20": "장흥군", "21": "진도군", "22": "함평군",
    "23": "해남군", "24": "화순군",
}
SIGUNGU_NAME_TO_CODE = {name: code for code, name in SIGUNGU_CODE_TO_NAME.items()}
HOURS_FIELDS = {
    "12": ("usetime",), "39": ("opentimefood",),
    "32": ("checkintime", "checkouttime"),
    "15": ("eventstartdate", "eventenddate"),
}
PARKING_FIELDS = {
    "12": ("parking",), "39": ("parkingfood",), "32": ("parkinglodging",),
}


class TourApiError(Exception):
    pass


@dataclass(frozen=True)
class RawSpot:
    content_id: str
    name: str
    category: str
    address: str
    latitude: Decimal
    longitude: Decimal
    description: str = ""
    hours: str = ""
    sigungu: str = ""
    parking_available: bool | None = None
    image_urls: list[str] = field(default_factory=list)


class TourApiClient:
    def __init__(self):
        self.base_url = settings.TOUR_API_BASE_URL.rstrip("/")
        self.service_key = settings.TOUR_API_SERVICE_KEY
        self.timeout = settings.TOUR_API_TIMEOUT_SEC

    def search_spots(self, *, keyword=None, category=None, sigungu=None) -> list[RawSpot]:
        endpoint = "searchKeyword2" if keyword else "areaBasedList2"
        params = {
            **self._base_params(), "areaCode": JEOLLANAM_DO_AREA_CODE,
            "pageNo": 1, "numOfRows": 100, "arrange": "A",
        }
        if keyword:
            params["keyword"] = keyword
        if category:
            params["contentTypeId"] = CATEGORY_TO_CONTENT_TYPE[category]
        if sigungu:
            params["sigunguCode"] = SIGUNGU_NAME_TO_CODE.get(sigungu, sigungu)
        return [
            self._raw_from_common(item)
            for item in self._get_items(endpoint, params)
            if str(item.get("contenttypeid", "")) in CONTENT_TYPE_TO_CATEGORY
        ]

    def get_spot_detail(self, *, content_id: str) -> RawSpot | None:
        # KorService2 rejects KorService1's detail selection parameters; the
        # required common fields (including overview) are returned by default.
        common = self._get_items("detailCommon2", {
            **self._base_params(), "contentId": content_id,
        })
        if not common:
            return None
        item = common[0]
        content_type = str(item.get("contenttypeid", ""))
        intro = self._get_items("detailIntro2", {
            **self._base_params(), "contentId": content_id,
            "contentTypeId": content_type,
        })
        images = self._get_items("detailImage2", {
            **self._base_params(), "contentId": content_id, "imageYN": "Y",
            "pageNo": 1, "numOfRows": 100,
        })
        image_urls = [image.get("originimgurl") for image in images if image.get("originimgurl")]
        if not image_urls and item.get("firstimage"):
            image_urls = [item["firstimage"]]
        return self._raw_from_common(
            item, intro=intro[0] if intro else {}, image_urls=image_urls
        )

    def _base_params(self):
        return {"serviceKey": self.service_key, "MobileOS": "ETC", "MobileApp": "Eodiganam", "_type": "json"}

    def _get_items(self, endpoint, params):
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            header = payload["response"]["header"]
            if header.get("resultCode") != "0000":
                raise TourApiError(header.get("resultMsg", "TourAPI error"))
            items = payload["response"]["body"].get("items", "")
            if not items:
                return []
            result = items.get("item", [])
            return result if isinstance(result, list) else [result]
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            raise TourApiError("TourAPI request failed") from exc

    def _raw_from_common(self, item, intro=None, image_urls=None):
        intro = intro or {}
        content_type = str(item.get("contenttypeid", ""))
        try:
            latitude = Decimal(str(item["mapy"]))
            longitude = Decimal(str(item["mapx"]))
            category = CONTENT_TYPE_TO_CATEGORY[content_type]
        except (KeyError, InvalidOperation) as exc:
            raise TourApiError("TourAPI response parsing failed") from exc
        hours = [str(intro[field]).strip() for field in HOURS_FIELDS.get(content_type, ()) if intro.get(field)]
        parking_values = [str(intro[field]).strip() for field in PARKING_FIELDS.get(content_type, ()) if intro.get(field)]
        parking_available = None
        if parking_values:
            parking_text = " ".join(parking_values)
            parking_available = not (
                any(word in parking_text for word in ("없음", "불가"))
                or parking_text.strip() == "무"
            )
        images = image_urls if image_urls is not None else ([item["firstimage"]] if item.get("firstimage") else [])
        return RawSpot(
            content_id=str(item["contentid"]), name=item.get("title", ""), category=category,
            address=" ".join(part for part in (item.get("addr1", ""), item.get("addr2", "")) if part),
            latitude=latitude, longitude=longitude, description=item.get("overview", ""),
            hours=" / ".join(hours),
            sigungu=SIGUNGU_CODE_TO_NAME.get(str(item.get("sigungucode", "")), item.get("sigungucode", "")),
            parking_available=parking_available, image_urls=images,
        )
