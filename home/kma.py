import math
import logging
from dataclasses import dataclass
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)

RE = 6371.00877
GRID = 5.0
SLAT1 = 30.0
SLAT2 = 60.0
OLON = 126.0
OLAT = 38.0
XO = 43
YO = 136
DEGRAD = math.pi / 180.0

_PTY_WEATHER = {
    "0": ("맑음", "clear"),
    "1": ("비", "rain"),
    "2": ("비/눈", "sleet"),
    "3": ("눈", "snow"),
    "4": ("소나기", "shower"),
    "5": ("비", "rain"),
    "6": ("비/눈", "sleet"),
    "7": ("눈", "snow"),
}


def latlng_to_grid(lat: float, lng: float) -> tuple[int, int]:
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(
        math.pi * 0.25 + slat1 * 0.5
    )
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lng * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    x = int(ra * math.sin(theta) + XO + 1.5)
    y = int(ro - ra * math.cos(theta) + YO + 1.5)
    return x, y


@dataclass(frozen=True)
class WeatherData:
    weather_type: str
    temp: float
    icon: str


class KmaClient:
    def __init__(self):
        self.base_url = settings.KMA_API_BASE_URL.rstrip("/")
        self.service_key = settings.KMA_API_SERVICE_KEY
        self.timeout = settings.KMA_API_TIMEOUT_SEC

    def get_current_weather(self, *, lat: float, lng: float) -> WeatherData | None:
        nx, ny = latlng_to_grid(lat, lng)
        base_date, base_time = self._latest_base_datetime()
        try:
            response = requests.get(
                f"{self.base_url}/getUltraSrtNcst",
                params={
                    "serviceKey": self.service_key,
                    "pageNo": 1,
                    "numOfRows": 10,
                    "dataType": "JSON",
                    "base_date": base_date,
                    "base_time": base_time,
                    "nx": nx,
                    "ny": ny,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()["response"]
            header = payload["header"]
            if header.get("resultCode") != "00":
                logger.warning("KMA API error (nx=%s, ny=%s): %s", nx, ny, header)
                return None
            items = payload["body"]["items"]["item"]
            values = {item["category"]: item["obsrValue"] for item in items}
            weather_type, icon = _PTY_WEATHER.get(
                str(values["PTY"]), ("맑음", "clear")
            )
            return WeatherData(
                weather_type=weather_type,
                temp=float(values["T1H"]),
                icon=icon,
            )
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "KMA weather fetch failed (nx=%s, ny=%s): %s", nx, ny, exc
            )
            return None

    def _latest_base_datetime(self) -> tuple[str, str]:
        now = timezone.localtime()
        if now.minute < 40:
            now -= timedelta(hours=1)
        return now.strftime("%Y%m%d"), now.strftime("%H00")
