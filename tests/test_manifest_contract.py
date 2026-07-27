import json
from pathlib import Path

import jsonschema

from pipeline.config import CensusConfig, FeedConfig
from pipeline.export.manifest import build_feed_entry, build_manifest

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "export" / "schema" / "manifest.schema.json"


def test_manifest_matches_schema(mini_feed, mini_gtfs_zip):
    feed_config = FeedConfig(
        id="mini-test",
        name="Mini Test Feed",
        region="Testville",
        agency_timezone="America/New_York",
        source_url="https://example.com/gtfs.zip",
        license="CC0",
        raw_path=mini_gtfs_zip,
        census=CensusConfig(state_fips="12", county_fips="011"),
    )
    entry = build_feed_entry(
        feed_config, mini_feed, "data", has_pmtiles=False, has_parquet=True
    )
    manifest = build_manifest([entry])

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=manifest, schema=schema)
