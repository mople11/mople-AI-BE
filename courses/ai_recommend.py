import json
from dataclasses import dataclass

import requests
from django.conf import settings

from common.exceptions import ApiError
from places.services import search_spots


class AIRecommendError(Exception):
    pass


@dataclass(frozen=True)
class RecommendedPlace:
    content_id: str
    order: int


@dataclass(frozen=True)
class AIRecommendation:
    name: str
    reason: str
    places: list[RecommendedPlace]


class AIRecommendClient:
    def __init__(self):
        self.base_url = settings.LLM_API_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_API_MODEL
        self.timeout = settings.LLM_API_TIMEOUT_SEC

    def recommend(
        self,
        *,
        mood: str,
        companion: str,
        transport: str,
        time_available: str,
        free_text: str,
    ) -> AIRecommendation:
        candidates = self._get_candidates(free_text=free_text)
        if not candidates:
            raise AIRecommendError("No candidate tourist spots")

        candidate_context = [
            {"name": spot.name, "content_id": spot.content_id}
            for spot in candidates
        ]
        prompt = {
            "mood": mood,
            "companion": companion,
            "transport": transport,
            "timeAvailable": time_available,
            "freeText": free_text,
            "candidates": candidate_context,
        }
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You recommend a Jeollanam-do travel course. Select only "
                                "content_id values from candidates. Return JSON with name, "
                                "reason, and places; places is an ordered array of objects "
                                "containing content_id. Select at least one place."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(prompt, ensure_ascii=False),
                        },
                    ],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            payload = json.loads(content)
            return self._parse_recommendation(payload, candidates)
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ) as exc:
            raise AIRecommendError("LLM recommendation failed") from exc

    def _get_candidates(self, *, free_text: str):
        keyword = free_text.strip() or None
        try:
            candidates = search_spots(
                keyword=keyword,
                category=None,
                region=None,
                sort=None,
            )
            if not candidates:
                candidates = search_spots(
                    keyword=None,
                    category=None,
                    region=None,
                    sort=None,
                )
            return candidates
        except ApiError as exc:
            raise AIRecommendError("Candidate search failed") from exc

    def _parse_recommendation(self, payload, candidates) -> AIRecommendation:
        candidate_ids = {spot.content_id for spot in candidates}
        raw_places = payload["places"]
        if not isinstance(raw_places, list) or not raw_places:
            raise ValueError("Recommendation has no places")

        content_ids = [str(item["content_id"]) for item in raw_places]
        if len(set(content_ids)) != len(content_ids):
            raise ValueError("Recommendation contains duplicate places")
        if any(content_id not in candidate_ids for content_id in content_ids):
            raise ValueError("Recommendation contains an unknown place")

        name = str(payload["name"]).strip()
        reason = str(payload["reason"]).strip()
        if not name or not reason:
            raise ValueError("Recommendation metadata is empty")
        return AIRecommendation(
            name=name,
            reason=reason,
            places=[
                RecommendedPlace(content_id=content_id, order=order)
                for order, content_id in enumerate(content_ids, start=1)
            ],
        )
