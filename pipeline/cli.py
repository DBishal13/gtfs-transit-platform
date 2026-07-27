"""Typer CLI entrypoints for the GTFS pipeline.

    python -m pipeline.cli all --feed broward-bct
    python -m pipeline.cli all --all-feeds
    python -m pipeline.cli ingest --feed broward-bct
    python -m pipeline.cli export --feed broward-bct
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from pipeline.analytics.comparison import build_comparison, summarize_feed
from pipeline.analytics.coverage import compute_coverage
from pipeline.analytics.duplication import compute_route_duplication
from pipeline.analytics.headway import compute_route_headway, compute_stop_headway
from pipeline.analytics.schedule_span import compute_schedule_span
from pipeline.analytics.spacing import compute_stop_spacing
from pipeline.config import FeedConfig, get_feed, load_feeds
from pipeline.export import metrics_export, parquet_export
from pipeline.export.manifest import build_feed_entry, build_manifest, write_manifest
from pipeline.export.tiles import build_pmtiles, export_routes_stops_geojson
from pipeline.ingest.gtfs_loader import GTFSFeed, load_gtfs
from pipeline.utils.logging import get_logger
from pipeline.validate.quick_checks import run_quick_checks
from pipeline.validate.report import build_quality_report
from pipeline.validate.run_gtfs_validator import run_official_validator

log = get_logger(__name__)
app = typer.Typer(add_completion=False)

DATA_URL_PREFIX = "data"  # relative prefix the manifest uses; app/public/data mirrors data/build


def _process_feed(feed_config: FeedConfig, build_root: Path, run_official: bool) -> dict:
    log.info("=== Processing feed '%s' (%s) ===", feed_config.id, feed_config.name)
    feed: GTFSFeed = load_gtfs(feed_config.raw_path, feed_config.id)
    out_dir = build_root / feed_config.id

    # --- validate ---
    quick_findings = run_quick_checks(feed)
    official_report = None
    if run_official:
        official_report = run_official_validator(feed_config.raw_path, out_dir / "_validator_raw")
    quality_report = build_quality_report(feed_config.id, quick_findings, official_report)
    metrics_export.export_quality(quality_report, out_dir / "quality.json")

    # --- analytics ---
    route_headway = compute_route_headway(feed)
    stop_headway = compute_stop_headway(feed)
    metrics_export.export_headway(route_headway, stop_headway, out_dir / "headway.json")

    spacing = compute_stop_spacing(feed)
    metrics_export.export_spacing(spacing, out_dir / "spacing.json")

    duplication = compute_route_duplication(feed)
    metrics_export.export_duplication(duplication, out_dir / "duplication.json")

    schedule_span = compute_schedule_span(feed)
    metrics_export.export_schedule_span(schedule_span, out_dir / "schedule_span.json")

    coverage = compute_coverage(feed, feed_config.census, feed_config.raw_path.parent / "census")
    metrics_export.export_coverage(coverage, out_dir / "coverage.json")

    metrics_export.export_routes_summary(feed.routes, out_dir / "routes_summary.json")

    # --- geo export ---
    geojson_paths = export_routes_stops_geojson(feed, out_dir)
    has_pmtiles = build_pmtiles(geojson_paths, out_dir / "transit.pmtiles")

    parquet_export.export_stop_times_parquet(feed, out_dir / "stop_times.parquet")

    manifest_entry = build_feed_entry(
        feed_config, feed, DATA_URL_PREFIX, has_pmtiles=has_pmtiles, has_parquet=True
    )
    summary = summarize_feed(feed, route_headway, coverage, quality_report)
    return {"manifest_entry": manifest_entry, "summary": summary}


@app.command()
def all(
    feed: Optional[str] = typer.Option(None, help="Feed id from data/feeds.yml"),
    all_feeds: bool = typer.Option(False, "--all-feeds", help="Process every feed in the registry"),
    build_dir: Path = typer.Option(Path("data/build"), help="Output directory for generated assets"),
    run_official_validator_flag: bool = typer.Option(
        True, "--run-official-validator/--no-official-validator",
        help="Attempt to run MobilityData's gtfs-validator (skipped automatically if Java/jar missing)",
    ),
) -> None:
    """Run ingest -> validate -> analyze -> export for one or all feeds, then write manifest.json."""
    if not feed and not all_feeds:
        typer.echo("Pass --feed <id> or --all-feeds", err=True)
        raise typer.Exit(1)

    feeds = load_feeds() if all_feeds else [get_feed(feed)]
    manifest_entries = []
    summaries = []
    for feed_config in feeds:
        result = _process_feed(feed_config, build_dir, run_official_validator_flag)
        manifest_entries.append(result["manifest_entry"])
        summaries.append(result["summary"])

    manifest = build_manifest(manifest_entries)
    write_manifest(manifest, build_dir / "manifest.json")

    comparison = build_comparison(summaries)
    metrics_export.export_comparison(comparison, build_dir / "comparison.json")

    log.info("Done. manifest.json + %d feed(s) written under %s", len(feeds), build_dir)


@app.command()
def ingest(feed: str, build_dir: Path = typer.Option(Path("data/build"))) -> None:
    """Load and summarize a feed without running analytics/export (fast sanity check)."""
    feed_config = get_feed(feed)
    gtfs_feed = load_gtfs(feed_config.raw_path, feed_config.id)
    typer.echo(
        f"{feed_config.id}: {len(gtfs_feed.routes)} routes, {len(gtfs_feed.trips)} trips, "
        f"{len(gtfs_feed.stops)} stops, {len(gtfs_feed.stop_times)} stop_times, "
        f"{len(gtfs_feed.shape_geoms)} shapes"
    )


if __name__ == "__main__":
    app()
