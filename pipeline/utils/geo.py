"""Geometry helpers shared across analytics modules."""

from __future__ import annotations

import geopandas as gpd
from pyproj import CRS

WGS84 = "EPSG:4326"


def utm_crs_for_lonlat(lon: float, lat: float) -> CRS:
    """Pick the UTM zone CRS covering a given lon/lat point, for meter-accurate buffering."""
    zone = int((lon + 180) // 6) + 1
    epsg = (32600 if lat >= 0 else 32700) + zone
    return CRS.from_epsg(epsg)


def to_projected(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject a WGS84 GeoDataFrame into the appropriate local UTM zone (meters)."""
    centroid = gdf.union_all().centroid
    crs = utm_crs_for_lonlat(centroid.x, centroid.y)
    return gdf.to_crs(crs)


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in meters. Used for quick spacing checks without reprojecting."""
    import math

    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))
