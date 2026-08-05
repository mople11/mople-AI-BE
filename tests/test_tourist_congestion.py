from unittest.mock import Mock, patch

from places.tourist_congestion import TouristCongestionClient


def api_response(items):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "response": {
            "header": {"resultCode": "0000", "resultMsg": "OK"},
            "body": {"items": {"item": items}},
        }
    }
    return response


@patch("places.tourist_congestion.requests.get")
def test_congestion_forecast_parses_current_and_recommended_date(
    mock_get, settings
):
    settings.TOUR_CONGESTION_API_SERVICE_KEY = "test-key"
    mock_get.return_value = api_response(
        [
            {
                "baseYmd": "20260805",
                "tAtsNm": "순천만 국가정원",
                "cnctrRate": "57.2",
            },
            {
                "baseYmd": "20260810",
                "tAtsNm": "순천만 국가정원",
                "cnctrRate": "21.5",
            },
        ]
    )

    result = TouristCongestionClient().get_forecast(
        spot_name="순천만 국가정원", sigungu="순천시"
    )

    assert result is not None
    assert result.level == "보통"
    assert result.concentration_rate == 57.2
    assert result.forecast_date == "2026-08-05"
    assert result.recommended_date == "2026-08-10"
    params = mock_get.call_args.kwargs["params"]
    assert params["areaCd"] == "46"
    assert params["signguCd"] == "46150"
    assert params["numOfRows"] == 1000
    assert "tAtsNm" not in params


@patch("places.tourist_congestion.requests.get")
def test_congestion_forecast_returns_none_for_empty_data(mock_get):
    mock_get.return_value = api_response([])

    result = TouristCongestionClient().get_forecast(
        spot_name="없는 관광지", sigungu="순천시"
    )

    assert result is None


def test_congestion_forecast_returns_none_for_unknown_region():
    result = TouristCongestionClient().get_forecast(
        spot_name="관광지", sigungu="알 수 없는 지역"
    )

    assert result is None
