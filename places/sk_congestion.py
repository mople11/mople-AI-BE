from dataclasses import dataclass


@dataclass(frozen=True)
class CongestionData:
    level: str
    hourly_graph: list[dict]
    recommended_time: str


class SkCongestionClient:
    def get_congestion(self, *, content_id: str) -> CongestionData | None:
        return None

