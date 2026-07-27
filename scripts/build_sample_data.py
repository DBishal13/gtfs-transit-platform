"""Builds the tiny sample dataset committed at app/public/data-sample/, so
`npm run dev` works without running the full Python/Java/tippecanoe pipeline.
Uses the same deterministic fixture as the pytest suite (tests/fixtures/mini_gtfs)
run through the real pipeline, so the sample is guaranteed to match the data
contract the app expects.

Usage: python scripts/build_sample_data.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "mini_gtfs"
SAMPLE_DIR = REPO_ROOT / "app" / "public" / "data-sample"


def main() -> None:
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from pipeline.analytics.comparison import build_comparison, summarize_feed
    from pipeline.analytics.coverage import compute_coverage
    from pipeline.analytics.duplication import compute_route_duplication
    from pipeline.analytics.headway import compute_route_headway, compute_stop_headway
    from pipeline.analytics.schedule_span import compute_schedule_span
    from pipeline.analytics.spacing import compute_stop_spacing
    from pipeline.config import FeedConfig
    from pipeline.export import metrics_export, parquet_export
    from pipeline.export.manifest import build_feed_entry, build_manifest, write_manifest
    from pipeline.export.tiles import build_pmtiles, export_routes_stops_geojson
    from pipeline.ingest.gtfs_loader import load_gtfs
    from pipeline.validate.quick_checks import run_quick_checks
    from pipeline.validate.report import build_quality_report

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = SAMPLE_DIR / "_mini_gtfs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for txt_file in FIXTURE_DIR.glob("*.txt"):
            zf.write(txt_file, arcname=txt_file.name)

    feed_config = FeedConfig(
        id="sample-feed",
        name="Sample Feed (tiny fixture)",
        region="Testville",
        agency_timezone="America/New_York",
        source_url="https://example.com/sample-gtfs.zip",
        license="CC0",
        raw_path=zip_path,
        census=None,
    )
    feed = load_gtfs(feed_config.raw_path, feed_config.id)
    out_dir = SAMPLE_DIR / feed_config.id

    findings = run_quick_checks(feed)
    quality_report = build_quality_report(feed_config.id, findings, None)
    metrics_export.export_quality(quality_report, out_dir / "quality.json")

    route_headway = compute_route_headway(feed)
    stop_headway = compute_stop_headway(feed)
    metrics_export.export_headway(route_headway, stop_headway, out_dir / "headway.json")

    metrics_export.export_spacing(compute_stop_spacing(feed), out_dir / "spacing.json")
    metrics_export.export_duplication(compute_route_duplication(feed), out_dir / "duplication.json")
    metrics_export.export_schedule_span(compute_schedule_span(feed), out_dir / "schedule_span.json")

    coverage = compute_coverage(feed, None, out_dir / "census")
    metrics_export.export_coverage(coverage, out_dir / "coverage.json")
    metrics_export.export_routes_summary(feed.routes, out_dir / "routes_summary.json")

    geojson_paths = export_routes_stops_geojson(feed, out_dir)
    has_pmtiles = build_pmtiles(geojson_paths, out_dir / "transit.pmtiles")
    parquet_export.export_stop_times_parquet(feed, out_dir / "stop_times.parquet")

    # Asset paths use the "data" prefix (not "data-sample") so this manifest is byte-for-byte
    # the shape the real pipeline produces — copy data-sample/* to app/public/data/ to use it.
    entry = build_feed_entry(feed_config, feed, "data", has_pmtiles=has_pmtiles, has_parquet=True)
    manifest = build_manifest([entry])
    write_manifest(manifest, SAMPLE_DIR / "manifest.json")

    summary = summarize_feed(feed, route_headway, coverage, quality_report)
    metrics_export.export_comparison(build_comparison([summary]), SAMPLE_DIR / "comparison.json")

    zip_path.unlink()
    print(f"Sample data written to {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
