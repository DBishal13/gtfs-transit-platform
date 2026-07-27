// Mirrors pipeline/export/schema/manifest.schema.json by hand (no shared
// runtime between Python and TypeScript). Keep in sync manually; the pipeline
// side has a contract test (tests/test_manifest_contract.py) that validates
// generated JSON against the JSON Schema this type should match.

export interface FeedAssets {
  routes_summary: string;
  headway: string;
  coverage: string;
  quality: string;
  spacing: string;
  duplication: string;
  schedule_span: string;
  routes_geojson: string;
  stops_geojson: string;
  tiles: string | null;
  stop_times_parquet: string | null;
}

export interface FeedCounts {
  routes: number;
  stops: number;
  trips: number;
}

export interface FeedEntry {
  id: string;
  name: string;
  region: string;
  source_url: string;
  license: string;
  bbox: [number, number, number, number];
  counts: FeedCounts;
  assets: FeedAssets;
  updated_at: string;
}

export interface Manifest {
  schema_version: number;
  generated_at: string;
  feeds: FeedEntry[];
}

export interface RouteHeadwayRow {
  route_id: string;
  direction_id: number;
  day_type: "weekday" | "saturday" | "sunday";
  time_bucket: string;
  avg_headway_min: number;
  trip_count: number;
}

export interface StopHeadwayRow {
  stop_id: string;
  day_type: "weekday" | "saturday" | "sunday";
  time_bucket: string;
  avg_headway_min: number;
  departure_count: number;
}

export interface HeadwayData {
  by_route: RouteHeadwayRow[];
  by_stop: StopHeadwayRow[];
}

export interface CoveragePopulationByBuffer {
  population_covered: number;
  pct_of_total_population: number | null;
}

export interface CoverageData {
  buffers_geojson: Record<string, GeoJSON.FeatureCollection | GeoJSON.Feature>;
  population: {
    total_population: number;
    by_buffer_m: Record<string, CoveragePopulationByBuffer>;
  } | null;
}

export interface QualityFinding {
  check: string;
  severity: "error" | "warning";
  message: string;
  count: number;
  sample: unknown[];
}

export interface QualityReport {
  feed_id: string;
  generated_at: string;
  official_validator: {
    ran: boolean;
    notice_count_by_severity: Record<string, number>;
    notice_types: { code: string; severity: string; total_notices: number }[];
  };
  custom_checks: QualityFinding[];
  summary: {
    status: "pass" | "warn" | "fail";
    custom_errors: number;
    custom_warnings: number;
    official_errors: number;
  };
}

export interface DuplicationRow {
  route_a: string;
  route_b: string;
  shared_stops: number;
  route_a_stops: number;
  route_b_stops: number;
  jaccard: number;
  high_overlap: boolean;
}

export interface SpacingRow {
  route_id: string;
  from_stop_id: string;
  to_stop_id: string;
  gap_m: number;
  is_outlier: boolean;
}

export interface ScheduleSpanRow {
  route_id: string;
  day_type: "weekday" | "saturday" | "sunday";
  trip_count: number;
  first_departure_min: number;
  last_arrival_min: number;
  span_hours: number;
}

export interface ComparisonFeedSummary {
  feed_id: string;
  route_count: number;
  stop_count: number;
  trip_count: number;
  avg_weekday_headway_min: number | null;
  pct_population_covered_400m: number | null;
  quality_status: "pass" | "warn" | "fail";
  quality_errors: number;
}

export interface ComparisonData {
  feeds: ComparisonFeedSummary[];
}

export interface RouteSummaryRow {
  route_id: string;
  route_short_name?: string;
  route_long_name?: string;
  route_color?: string;
}
