"""Tests for geocoding_service.py using a mocked httpx.get — no network or database
required, so these always run regardless of docker compose availability.
"""

from __future__ import annotations

import pytest

from service.app.config import Settings
from service.app.services import geocoding_service


class _FakeResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    def raise_for_status(self) -> None:
        pass

    def json(self):
        return self._json_data


def test_nominatim_geocoder_returns_result(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        assert "search" in url
        assert params["q"] == "unique-query-1"
        return _FakeResponse([{"lon": "-80.1", "lat": "26.1", "display_name": "Somewhere, FL"}])

    monkeypatch.setattr(geocoding_service.httpx, "get", fake_get)
    geocoder = geocoding_service.NominatimGeocoder(
        base_url="https://nominatim.example.com", user_agent="test-agent"
    )
    result = geocoder.geocode("unique-query-1")
    assert result is not None
    assert result.lon == -80.1
    assert result.lat == 26.1
    assert result.display_name == "Somewhere, FL"


def test_nominatim_geocoder_returns_none_when_no_match(monkeypatch):
    monkeypatch.setattr(geocoding_service.httpx, "get", lambda *a, **k: _FakeResponse([]))
    geocoder = geocoding_service.NominatimGeocoder(
        base_url="https://nominatim.example.com", user_agent="test-agent"
    )
    assert geocoder.geocode("unique-query-2-no-match") is None


def test_mapbox_geocoder_returns_result(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert "mapbox.places" in url
        return _FakeResponse({"features": [{"center": [-80.2, 26.2], "place_name": "Mapbox Place"}]})

    monkeypatch.setattr(geocoding_service.httpx, "get", fake_get)
    geocoder = geocoding_service.MapboxGeocoder(api_key="fake-key")
    result = geocoder.geocode("some query")
    assert result is not None
    assert result.lon == -80.2
    assert result.lat == 26.2
    assert result.display_name == "Mapbox Place"


def test_get_geocoding_provider_defaults_to_nominatim():
    settings = Settings(geocoder_provider="nominatim")
    provider = geocoding_service.get_geocoding_provider(settings)
    assert isinstance(provider, geocoding_service.NominatimGeocoder)


def test_get_geocoding_provider_selects_mapbox_when_configured():
    settings = Settings(geocoder_provider="mapbox", mapbox_api_key="fake-key")
    provider = geocoding_service.get_geocoding_provider(settings)
    assert isinstance(provider, geocoding_service.MapboxGeocoder)


def test_get_geocoding_provider_mapbox_requires_api_key():
    settings = Settings(geocoder_provider="mapbox", mapbox_api_key=None)
    with pytest.raises(RuntimeError):
        geocoding_service.get_geocoding_provider(settings)
