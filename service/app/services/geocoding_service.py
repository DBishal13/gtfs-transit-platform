"""Address/place -> coordinates geocoding, provider-abstracted (mirrors the LLM provider
pattern added in Phase 4's service/app/services/agent/llm_provider.py) so a paid provider
can be swapped in via config without touching callers.

Default provider is Nominatim's public instance: free, no API key, but rate-limited to
roughly 1 request/second and requires a descriptive User-Agent per its usage policy
(https://operations.osmfoundation.org/policies/nominatim/) — mirrors the project's
existing "degrade gracefully without a paid key" pattern already used for Census data in
pipeline/ingest/census.py. Fine for a portfolio demo; self-host Nominatim or switch
GEOCODER_PROVIDER=mapbox for production query volume.
"""

from __future__ import annotations

import functools
from typing import Protocol

import httpx
from pydantic import BaseModel

from service.app.config import Settings


class GeocodeResult(BaseModel):
    lon: float
    lat: float
    display_name: str


class GeocodingProvider(Protocol):
    def geocode(self, query: str) -> GeocodeResult | None: ...


@functools.lru_cache(maxsize=256)
def _cached_nominatim_search(base_url: str, user_agent: str, query: str) -> tuple[dict, ...]:
    """Addresses repeat across queries (e.g. an agent re-resolving the same landmark
    across turns), so cache raw results in-process rather than re-hitting Nominatim's
    rate-limited public API every time."""
    response = httpx.get(
        f"{base_url}/search",
        params={"q": query, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": user_agent},
        timeout=10.0,
    )
    response.raise_for_status()
    return tuple(response.json())


class NominatimGeocoder:
    def __init__(self, *, base_url: str, user_agent: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent

    def geocode(self, query: str) -> GeocodeResult | None:
        results = _cached_nominatim_search(self._base_url, self._user_agent, query)
        if not results:
            return None
        top = results[0]
        return GeocodeResult(
            lon=float(top["lon"]), lat=float(top["lat"]), display_name=top["display_name"]
        )


class MapboxGeocoder:
    """A second GeocodingProvider implementation — proof the abstraction actually swaps
    providers rather than just describing that it could. Not exercised by default config
    (requires MAPBOX_API_KEY) or by the default test suite."""

    def __init__(self, *, api_key: str) -> None:
        self._api_key = api_key

    def geocode(self, query: str) -> GeocodeResult | None:
        response = httpx.get(
            f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json",
            params={"access_token": self._api_key, "limit": 1},
            timeout=10.0,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
        if not features:
            return None
        top = features[0]
        lon, lat = top["center"]
        return GeocodeResult(lon=lon, lat=lat, display_name=top.get("place_name", query))


def get_geocoding_provider(settings: Settings) -> GeocodingProvider:
    if settings.geocoder_provider == "mapbox":
        if not settings.mapbox_api_key:
            raise RuntimeError("GEOCODER_PROVIDER=mapbox requires MAPBOX_API_KEY to be set")
        return MapboxGeocoder(api_key=settings.mapbox_api_key)
    return NominatimGeocoder(
        base_url=settings.nominatim_base_url, user_agent=settings.nominatim_user_agent
    )
