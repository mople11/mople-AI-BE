from dataclasses import dataclass


@dataclass(frozen=True)
class TrafficData:
    segments: list[dict]
    eta_min: int
    alt_route: dict


class KakaoMobilityClient:
    def get_traffic(
        self, *, origin: tuple[float, float], destination: tuple[float, float]
    ) -> TrafficData | None:
        return None

