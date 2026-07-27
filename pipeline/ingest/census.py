"""Population data for coverage analysis, from the US Census Bureau (public, free, no key
required for the small ACS pulls this project makes).

Two datasets are combined per county:
  - TIGER/Line block group boundaries (geometry)
  - ACS 5-year total population estimate (B01003_001E) per block group

Both are cached under data/raw/<feed_id>/census/ so the network is only hit once
per county. If either fetch fails (no network, Census API change, unsupported
country/region for a non-US feed), callers should catch and degrade to
buffer-only coverage rather than failing the whole pipeline.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from pipeline.config import CensusConfig
from pipeline.utils.logging import get_logger

log = get_logger(__name__)

ACS_YEAR = 2022
TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER{year}/BG/tl_{year}_{state}_bg.zip"
ACS_URL = "https://api.census.gov/data/{year}/acs/acs5"
POPULATION_VARIABLE = "B01003_001E"


def _fetch_block_group_boundaries(state_fips: str, cache_dir: Path) -> gpd.GeoDataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / f"tl_{ACS_YEAR}_{state_fips}_bg.zip"
    if not zip_path.exists():
        url = TIGER_URL.format(year=ACS_YEAR, state=state_fips)
        log.info("Downloading TIGER/Line block group boundaries from %s", url)
        resp = requests.get(url, timeout=60, headers={"User-Agent": "gtfs-transit-platform/0.1"})
        resp.raise_for_status()
        zip_path.write_bytes(resp.content)
    return gpd.read_file(zip_path)


def _fetch_population(state_fips: str, county_fips: str) -> pd.DataFrame:
    params = {
        "get": f"NAME,{POPULATION_VARIABLE}",
        "for": "block group:*",
        "in": f"state:{state_fips} county:{county_fips}",
    }
    api_key = os.environ.get("CENSUS_API_KEY")
    if api_key:
        params["key"] = api_key
    url = ACS_URL.format(year=ACS_YEAR)
    resp = requests.get(url, params=params, timeout=30, headers={"User-Agent": "gtfs-transit-platform/0.1"})
    content_type = resp.headers.get("Content-Type", "")
    if "json" not in content_type:
        # The API redirects to an HTML "missing key" page (not JSON) when no key is
        # supplied and the request is large/rate-limited enough to require one.
        raise RuntimeError(
            "Census ACS API did not return JSON (likely requires a free API key). Set "
            "the CENSUS_API_KEY environment variable (sign up at "
            "https://api.census.gov/data/key_signup.html) to enable population-weighted "
            "coverage; otherwise coverage falls back to buffer-only."
        )
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["GEOID"] = df["state"] + df["county"] + df["tract"] + df["block group"]
    df["population"] = pd.to_numeric(df[POPULATION_VARIABLE], errors="coerce").fillna(0)
    return df[["GEOID", "population"]]


def fetch_population_block_groups(census: CensusConfig, cache_dir: Path) -> gpd.GeoDataFrame:
    """Return block-group polygons for one county with a `population` column, in WGS84."""
    boundaries = _fetch_block_group_boundaries(census.state_fips, cache_dir)
    boundaries = boundaries[boundaries["COUNTYFP"] == census.county_fips].copy()

    population = _fetch_population(census.state_fips, census.county_fips)
    merged = boundaries.merge(population, on="GEOID", how="left")
    merged["population"] = merged["population"].fillna(0)

    if merged.crs is None:
        merged = merged.set_crs("EPSG:4269")  # NAD83, TIGER/Line's native CRS
    merged = merged.to_crs("EPSG:4326")

    log.info(
        "Loaded %d Census block groups (%s total population) for state=%s county=%s",
        len(merged),
        int(merged["population"].sum()),
        census.state_fips,
        census.county_fips,
    )
    return merged[["GEOID", "population", "geometry"]]
