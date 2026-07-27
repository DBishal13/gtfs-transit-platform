"""Stop accessibility / coverage analysis: walk-buffer polygons around stops,
optionally weighted by Census block-group population (areal-weighted, i.e. a
block group's population is apportioned to the buffer in proportion to the
share of its area the buffer covers — a standard, simple approximation given
we only have block-group-level, not parcel-level, population).

Degrades gracefully: if population data can't be fetched (no network, county
not covered, non-US feed), buffer polygons and area-based stats are still
returned with `population` set to None.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from pipeline.config import CensusConfig
from pipeline.ingest.census import fetch_population_block_groups
from pipeline.ingest.gtfs_loader import GTFSFeed
from pipeline.utils.geo import WGS84, to_projected
from pipeline.utils.logging import get_logger

log = get_logger(__name__)

BUFFER_DISTANCES_M = [400, 800]  # ~5 min and ~10 min walk


SIMPLIFY_TOLERANCE_M = 15  # keeps buffer polygons visually smooth while bounding vertex count


def _dissolved_buffer(stops_proj: gpd.GeoDataFrame, distance_m: int):
    dissolved = stops_proj.buffer(distance_m).union_all()
    return dissolved.simplify(SIMPLIFY_TOLERANCE_M, preserve_topology=True)


def compute_coverage(
    feed: GTFSFeed, census: CensusConfig | None, cache_dir: Path
) -> dict:
    stops_proj = to_projected(feed.stops)
    working_crs = stops_proj.crs

    buffers_wgs84: dict[int, gpd.GeoDataFrame] = {}
    buffer_geoms_proj = {}
    for distance in BUFFER_DISTANCES_M:
        geom = _dissolved_buffer(stops_proj, distance)
        buffer_geoms_proj[distance] = geom
        buffers_wgs84[distance] = gpd.GeoDataFrame(geometry=[geom], crs=working_crs).to_crs(WGS84)

    result: dict = {
        "buffers_geojson": {
            str(distance): gdf.__geo_interface__ for distance, gdf in buffers_wgs84.items()
        },
        "population": None,
    }

    if census is None:
        log.info("No census config for this feed; skipping population-weighted coverage.")
        return result

    try:
        block_groups = fetch_population_block_groups(census, cache_dir)
        block_groups_proj = block_groups.to_crs(working_crs)
        block_groups_proj["area_m2"] = block_groups_proj.geometry.area

        total_population = float(block_groups_proj["population"].sum())
        population_stats = {}
        for distance, geom in buffer_geoms_proj.items():
            intersection_area = block_groups_proj.geometry.intersection(geom).area
            share = (intersection_area / block_groups_proj["area_m2"]).clip(upper=1.0).fillna(0.0)
            covered_population = float((share * block_groups_proj["population"]).sum())
            population_stats[str(distance)] = {
                "population_covered": round(covered_population, 0),
                "pct_of_total_population": round(
                    100 * covered_population / total_population, 1
                ) if total_population else None,
            }

        result["population"] = {
            "total_population": round(total_population, 0),
            "by_buffer_m": population_stats,
        }
    except Exception:
        log.warning(
            "Population-weighted coverage failed (network/Census API issue); "
            "returning buffer-only coverage.", exc_info=True,
        )

    return result
