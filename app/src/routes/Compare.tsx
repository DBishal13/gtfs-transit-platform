import { useEffect, useState } from "react";
import GroupedBarChart from "../components/charts/GroupedBarChart";
import { fetchComparison } from "../lib/manifest";
import type { ComparisonData } from "../types/dataContract";

function StatusBadge({ status }: { status: "pass" | "warn" | "fail" }) {
  return <span className={`badge badge--${status}`}>{status.toUpperCase()}</span>;
}

export default function Compare() {
  const [data, setData] = useState<ComparisonData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchComparison<ComparisonData>()
      .then(setData)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page empty-state">Loading comparison data…</div>;
  if (error) return <div className="page empty-state">Couldn't load comparison data: {error}</div>;
  if (!data || data.feeds.length === 0) return <div className="page empty-state">No feeds to compare.</div>;

  return (
    <div className="page">
      <h1>Compare Feeds</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Top-line service metrics across every feed currently loaded in this deployment.
      </p>

      {data.feeds.length > 1 && (
        <div className="card">
          <h3>Average weekday headway (minutes)</h3>
          <GroupedBarChart
            categories={data.feeds.map((f) => f.feed_id)}
            series={[
              {
                key: "headway",
                label: "Avg weekday headway",
                color: "var(--series-1)",
                values: data.feeds.map((f) => f.avg_weekday_headway_min),
              },
            ]}
            valueSuffix=" min"
            ariaLabel="Average weekday headway by feed"
          />
        </div>
      )}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Feed</th>
              <th>Routes</th>
              <th>Stops</th>
              <th>Trips</th>
              <th>Avg weekday headway</th>
              <th>Pop. covered (400m)</th>
              <th>Quality</th>
            </tr>
          </thead>
          <tbody>
            {data.feeds.map((f) => (
              <tr key={f.feed_id}>
                <td>{f.feed_id}</td>
                <td>{f.route_count}</td>
                <td>{f.stop_count}</td>
                <td>{f.trip_count}</td>
                <td>{f.avg_weekday_headway_min != null ? `${f.avg_weekday_headway_min} min` : "—"}</td>
                <td>
                  {f.pct_population_covered_400m != null
                    ? `${f.pct_population_covered_400m.toFixed(1)}%`
                    : "—"}
                </td>
                <td>
                  <StatusBadge status={f.quality_status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
