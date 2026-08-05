from unittest.mock import Mock, patch

from places.kakao_mobility import KakaoMobilityClient


@patch("places.kakao_mobility.requests.get")
def test_kakao_directions_parses_traffic_and_alternative(mock_get, settings):
    settings.KAKAO_MOBILITY_REST_API_KEY = "test-key"
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "routes": [
            {
                "result_code": 0,
                "summary": {"duration": 901},
                "sections": [
                    {
                        "roads": [
                            {
                                "name": "남해고속도로",
                                "distance": 1000,
                                "traffic_state": 3,
                            }
                        ]
                    }
                ],
            },
            {
                "result_code": 0,
                "summary": {"duration": 721},
                "sections": [],
            },
        ]
    }
    mock_get.return_value = response

    result = KakaoMobilityClient().get_traffic(
        origin=(34.8, 126.4), destination=(34.9, 127.5)
    )

    assert result is not None
    assert result.eta_min == 16
    assert result.segments == [{"section": "남해고속도로", "level": "정체"}]
    assert result.alt_route == {"available": True, "etaMin": 13}
    assert mock_get.call_args.kwargs["headers"] == {
        "Authorization": "KakaoAK test-key"
    }
    assert mock_get.call_args.kwargs["params"]["origin"] == "126.4,34.8"


@patch("places.kakao_mobility.requests.get")
def test_kakao_directions_returns_none_without_valid_route(mock_get):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "routes": [{"result_code": 104, "result_msg": "경로 없음"}]
    }
    mock_get.return_value = response

    result = KakaoMobilityClient().get_traffic(
        origin=(34.8, 126.4), destination=(34.9, 127.5)
    )

    assert result is None
