from dataclasses import dataclass
from math import ceil

import requests
from django.conf import settings


@dataclass(frozen=True)
class TrafficData:
    segments: list[dict]
    eta_min: int
    alt_route: dict


class KakaoMobilityClient:
    TRAFFIC_LEVELS = {0: "정보없음", 1: "원활", 2: "서행", 3: "정체"}

    def __init__(self):
        self.base_url = settings.KAKAO_MOBILITY_BASE_URL.rstrip("/")
        self.api_key = settings.KAKAO_MOBILITY_REST_API_KEY
        self.timeout = settings.KAKAO_MOBILITY_TIMEOUT_SEC

    def get_traffic(
        self, *, origin: tuple[float, float], destination: tuple[float, float]
    ) -> TrafficData | None:
        try:
            response = requests.get(
                f"{self.base_url}/directions",
                headers={"Authorization": f"KakaoAK {self.api_key}"},
                params={
                    "origin": f"{origin[1]},{origin[0]}",
                    "destination": f"{destination[1]},{destination[0]}",
                    "alternatives": "true",
                    "road_details": "true",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            routes = response.json().get("routes", [])
            valid_routes = [
                route for route in routes if route.get("result_code") == 0
            ]
            if not valid_routes:
                return None
            primary = valid_routes[0]
            segments = self._segments(primary)
            alternatives = valid_routes[1:]
            alt_route = {"available": bool(alternatives), "etaMin": None}
            if alternatives:
                alt_route["etaMin"] = ceil(
                    alternatives[0]["summary"]["duration"] / 60
                )
            return TrafficData(
                segments=segments,
                eta_min=ceil(primary["summary"]["duration"] / 60),
                alt_route=alt_route,
            )
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
        ):
            return None

    def _segments(self, route: dict) -> list[dict]:
        segments = []
        for section in route.get("sections", []):
            for road in section.get("roads", []):
                if not road.get("distance"):
                    continue
                segments.append(
                    {
                        "section": road.get("name") or "이름 없는 도로",
                        "level": self.TRAFFIC_LEVELS.get(
                            road.get("traffic_state"), "정보없음"
                        ),
                    }
                )
        return segments
