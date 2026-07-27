import { useMemo, useState } from "react";
import GroupedBarChart from "../components/charts/GroupedBarChart";
import { useFeedContext } from "../lib/FeedContext";
import { useFeedAsset } from "../lib/useFeedAsset";
import type { HeadwayData, RouteSummaryRow } from "../types/dataContract";

const TIME_BUCKETS = ["early_am", "am_peak", "midday", "pm_peak", "evening", "night"];
const DAY_TYPES: { key: HeadwayData["by_route"][number]["day_type"]; label: string; color: string }[] = [
  { key: "weekday", label: "Weekday", color: "var(--series-1)" },
  { key: "saturday", label: "Saturday", color: "var(--series-2)" },
  { key: "sunday", label: "Sunday", color: "var(--series-3)" },
];

export default function Headway() {
  const { selectedFeed } = useFeedContext();
  const { data: routes } = useFeedAsset<RouteSummaryRow[]>(selectedFeed?.assets.routes_summary);
  const { data: headway, loading, error } = useFeedAsset<HeadwayData>(selectedFeed?.assets.headway);
  const [routeId, setRouteId] = useState<string | null>(null);

  const activeRouteId = routeId ?? routes?.[0]?.route_id ?? null;

  const series = useMemo(() => {
    if (!headway || !activeRouteId) return [];
    const rows = headway.by_route.filter((r) => r.route_id === activeRouteId);
    return DAY_TYPES.map((dt) => ({
      key: dt.key,
      label: dt.label,
      color: dt.color,
      values: TIME_BUCKETS.map((bucket) => {
        const match = rows.find((r) => r.day_type === dt.key && r.time_bucket === bucket);
        return match ? match.avg_headway_min : null;
      }),
    }));
  }, [headway, activeRouteId]);

  if (loading) return <div className="page empty-state">Loading headway data…</div>;
  if (error) return <div className="page empty-state">Couldn't load headway data: {error}</div>;

  return (
    <div className="page">
      <h1>Service Frequency</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Average minutes between scheduled departures, by time of day. Computed from the static
        GTFS schedule (stop_times + calendar) — not realtime.
      </p>

      <div className="card">
        <label htmlFor="route-select" style={{ marginRight: "0.5rem", color: "var(--text-muted)" }}>
          Route
        </label>
        <select
          id="route-select"
          value={activeRouteId ?? ""}
          onChange={(e) => setRouteId(e.target.value)}
        >
          {routes?.map((r) => (
            <option key={r.route_id} value={r.route_id}>
              {r.route_short_name ?? r.route_id} — {r.route_long_name ?? ""}
            </option>
          ))}
        </select>

        {series.every((s) => s.values.every((v) => v == null)) ? (
          <div className="empty-state">No scheduled service found for this route.</div>
        ) : (
          <GroupedBarChart
            categories={TIME_BUCKETS}
            series={series}
            valueSuffix=" min"
            ariaLabel={`Average headway by time of day for route ${activeRouteId}`}
          />
        )}
      </div>
    </div>
  );
}
