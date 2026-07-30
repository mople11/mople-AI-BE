from unittest.mock import patch

import pytest

from places.kakao_mobility import TrafficData


PARAMS = {"origin.lat": 34.8, "origin.lng": 126.4, "destination.lat": 34.9, "destination.lng": 127.5}


@pytest.mark.django_db
@patch("places.services.KakaoMobilityClient.get_traffic", return_value=None)
def test_traffic_unavailable_returns_empty_data(mock_traffic, api_client):
    response = api_client.get("/api/v1/traffic/congestion", PARAMS)
    assert response.status_code == 200
    assert response.data == {"success": True, "data": {}, "error": None}
    mock_traffic.assert_called_once_with(origin=(34.8, 126.4), destination=(34.9, 127.5))


@pytest.mark.django_db
@patch("places.services.KakaoMobilityClient.get_traffic")
def test_traffic_success_contract(mock_traffic, api_client):
    mock_traffic.return_value = TrafficData(segments=[{"section": "A", "level": "원활"}], eta_min=15, alt_route={"available": True, "etaMin": 12})
    response = api_client.get("/api/v1/traffic/congestion", PARAMS)
    assert response.status_code == 200
    assert response.data["data"] == {"segments": [{"section": "A", "level": "원활"}], "etaMin": 15, "altRoute": {"available": True, "etaMin": 12}}


@pytest.mark.django_db
def test_traffic_requires_all_coordinates(api_client):
    response = api_client.get("/api/v1/traffic/congestion", {"origin.lat": 34.8})
    assert response.status_code == 422
    assert response.data["error"]["code"] == "COMMON_422"

