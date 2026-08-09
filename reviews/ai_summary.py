import json
from dataclasses import dataclass

import requests
from django.conf import settings


class AISummaryError(Exception):
    pass


@dataclass(frozen=True)
class ReviewSummaryResult:
    score: int
    positive: list[str]
    negative: list[str]


class AISummaryClient:
    def __init__(self):
        self.base_url = settings.LLM_API_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_API_MODEL
        self.timeout = settings.LLM_API_TIMEOUT_SEC

    def summarize(self, *, reviews: list[str]) -> ReviewSummaryResult:
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
                                "Analyze tourist spot reviews. Return JSON with score "
                                "(an integer from 0 to 100), positive (an array of "
                                "positive keywords), and negative (an array of negative "
                                "keywords)."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(
                                {"reviews": reviews}, ensure_ascii=False
                            ),
                        },
                    ],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_summary(json.loads(content))
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ) as exc:
            raise AISummaryError("LLM review summary failed") from exc

    def _parse_summary(self, payload) -> ReviewSummaryResult:
        score = payload["score"]
        positive = payload["positive"]
        negative = payload["negative"]
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
            raise ValueError("Summary score is invalid")
        if not isinstance(positive, list) or not isinstance(negative, list):
            raise ValueError("Summary keywords are invalid")
        if any(not isinstance(keyword, str) for keyword in [*positive, *negative]):
            raise ValueError("Summary keywords must be strings")
        return ReviewSummaryResult(
            score=score,
            positive=positive,
            negative=negative,
        )
