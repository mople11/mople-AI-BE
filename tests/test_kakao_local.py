from unittest.mock import Mock, patch

import pytest
import requests

from gamification.kakao_local import KakaoLocalClient


@patch("gamification.kakao_local.requests.get")
def test_get_city_code_parses_legal_dong(mock_get, settings):
    settings.KAKAO_REST_API_KEY = "test-key"
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "documents": [
            {
                "region_type": "H",
                "region_1depth_name": "전라남도",
                "region_2depth_name": "여수시",
            },
            {
                "region_type": "B",
                "region_1depth_name": "전라남도",
                "region_2depth_name": "여수시",
            },
        ]
    }
    mock_get.return_value = response

    city_code = KakaoLocalClient().get_city_code(lat=34.76, lng=127.66)

    assert city_code == "46130"
    assert mock_get.call_args.kwargs["params"] == {"x": 127.66, "y": 34.76}
    assert mock_get.call_args.kwargs["headers"] == {
        "Authorization": "KakaoAK test-key"
    }


@pytest.mark.parametrize(
    "documents",
    [
        [],
        [
            {
                "region_type": "B",
                "region_1depth_name": "서울특별시",
                "region_2depth_name": "강남구",
            }
        ],
        [
            {
                "region_type": "B",
                "region_1depth_name": "전라남도",
                "region_2depth_name": "알수없는시",
            }
        ],
    ],
)
@patch("gamification.kakao_local.requests.get")
def test_get_city_code_returns_none_when_region_does_not_match(
    mock_get, documents
):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"documents": documents}
    mock_get.return_value = response

    assert KakaoLocalClient().get_city_code(lat=37.5, lng=127.0) is None


@patch("gamification.kakao_local.requests.get")
def test_get_city_code_logs_request_failure(mock_get, caplog):
    mock_get.side_effect = requests.Timeout("timed out")

    with caplog.at_level("WARNING", logger="gamification.kakao_local"):
        city_code = KakaoLocalClient().get_city_code(lat=34.76, lng=127.66)

    assert city_code is None
    assert "Kakao Local API call failed" in caplog.text


@patch("gamification.kakao_local.requests.get")
def test_get_city_code_handles_unexpected_json_shape(mock_get, caplog):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = []
    mock_get.return_value = response

    with caplog.at_level("WARNING", logger="gamification.kakao_local"):
        city_code = KakaoLocalClient().get_city_code(lat=34.76, lng=127.66)

    assert city_code is None
    assert "Kakao Local API call failed" in caplog.text
