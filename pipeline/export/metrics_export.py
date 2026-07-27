"""Writes the small precomputed JSON files each dashboard page reads directly
(no duckdb-wasm needed for these — see parquet_export.py for the ad hoc path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _write_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def export_routes_summary(routes: pd.DataFrame, out_path: Path) -> None:
    cols = [c for c in ["route_id", "route_short_name", "route_long_name", "route_color"] if c in routes.columns]
    _write_json(routes[cols].to_dict(orient="records"), out_path)


def export_headway(route_headway: pd.DataFrame, stop_headway: pd.DataFrame, out_path: Path) -> None:
    _write_json(
        {
            "by_route": route_headway.to_dict(orient="records"),
            "by_stop": stop_headway.to_dict(orient="records"),
        },
        out_path,
    )


def export_coverage(coverage: dict, out_path: Path) -> None:
    _write_json(coverage, out_path)


def export_quality(quality_report: dict, out_path: Path) -> None:
    _write_json(quality_report, out_path)


def export_spacing(spacing: pd.DataFrame, out_path: Path) -> None:
    _write_json(spacing.to_dict(orient="records"), out_path)


def export_duplication(duplication: pd.DataFrame, out_path: Path) -> None:
    _write_json(duplication.to_dict(orient="records"), out_path)


def export_schedule_span(schedule_span: pd.DataFrame, out_path: Path) -> None:
    _write_json(schedule_span.to_dict(orient="records"), out_path)


def export_comparison(comparison: dict, out_path: Path) -> None:
    _write_json(comparison, out_path)
