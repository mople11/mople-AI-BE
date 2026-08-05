from dataclasses import dataclass
from datetime import datetime
from math import ceil

import requests
from django.conf import settings


JEOLLANAM_DO_AREA_CODE = "46"
SIGUNGU_NAME_TO_CODE = {
    "목포시": "46110",
    "여수시": "46130",
    "순천시": "46150",
    "나주시": "46170",
    "광양시": "46230",
    "담양군": "46710",
    "곡성군": "46720",
    "구례군": "46730",
    "고흥군": "46770",
    "보성군": "46780",
    "화순군": "46790",
    "장흥군": "46800",
    "강진군": "46810",
    "해남군": "46820",
    "영암군": "46830",
    "무안군": "46840",
    "함평군": "46860",
    "영광군": "46870",
    "장성군": "46880",
    "완도군": "46890",
    "진도군": "46900",
    "신안군": "46910",
}


@dataclass(frozen=True)
class CongestionForecast:
    level: str
    concentration_rate: float
    forecast_date: str
    recommended_date: str


class TouristCongestionClient:
    def __init__(self):
        self.base_url = settings.TOUR_CONGESTION_API_BASE_URL.rstrip("/")
        self.service_key = settings.TOUR_CONGESTION_API_SERVICE_KEY
        self.timeout = settings.TOUR_CONGESTION_API_TIMEOUT_SEC

    def get_forecast(
        self, *, spot_name: str, sigungu: str
    ) -> CongestionForecast | None:
        sigungu_code = SIGUNGU_NAME_TO_CODE.get(sigungu)
        if not sigungu_code:
            return None

        try:
            forecasts = self._fetch_forecasts(
                spot_name=spot_name, sigungu_code=sigungu_code
            )
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
        ):
            return None

        if not forecasts:
            return None
        forecast_date, rate = forecasts[0]
        recommended_date, _ = min(forecasts, key=lambda item: item[1])
        return CongestionForecast(
            level=self._level(rate),
            concentration_rate=round(rate, 2),
            forecast_date=forecast_date,
            recommended_date=recommended_date,
        )

    def _fetch_forecasts(
        self, *, spot_name: str, sigungu_code: str
    ) -> list[tuple[str, float]]:
        rows_per_page = 1000
        page = 1
        while True:
            response = requests.get(
                f"{self.base_url}/tatsCnctrRatedList",
                params={
                    "serviceKey": self.service_key,
                    "MobileOS": "ETC",
                    "MobileApp": "Eodiganam",
                    "_type": "json",
                    "pageNo": page,
                    "numOfRows": rows_per_page,
                    "areaCd": JEOLLANAM_DO_AREA_CODE,
                    "signguCd": sigungu_code,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            header = payload["response"]["header"]
            if header.get("resultCode") != "0000":
                return []
            body = payload["response"]["body"]
            items = body.get("items", "")
            raw_items = items.get("item", []) if items else []
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
            matched = [
                (
                    self._format_date(item["baseYmd"]),
                    float(item["cnctrRate"]),
                )
                for item in raw_items
                if item.get("tAtsNm") == spot_name
            ]
            if matched:
                return matched
            total_count = int(body.get("totalCount", len(raw_items)))
            if page >= ceil(total_count / rows_per_page):
                return []
            page += 1

    @staticmethod
    def _format_date(value: str) -> str:
        return datetime.strptime(value, "%Y%m%d").date().isoformat()

    @staticmethod
    def _level(rate: float) -> str:
        if rate < 34:
            return "여유"
        if rate < 67:
            return "보통"
        return "혼잡"
