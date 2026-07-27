import CoverageMap from "../components/map/CoverageMap";
import { useFeedContext } from "../lib/FeedContext";
import { useFeedAsset } from "../lib/useFeedAsset";
import type { CoverageData } from "../types/dataContract";

function pct(value: number | null): string {
  return value == null ? "—" : `${value.toFixed(1)}%`;
}

export default function Coverage() {
  const { selectedFeed } = useFeedContext();
  const { data: coverage, loading, error } = useFeedAsset<CoverageData>(
    selectedFeed?.assets.coverage,
  );

  if (loading) return <div className="page empty-state">Loading coverage data…</div>;
  if (error) return <div className="page empty-state">Couldn't load coverage data: {error}</div>;
  if (!coverage || !selectedFeed) return <div className="page empty-state">No data.</div>;

  const pop400 = coverage.population?.by_buffer_m["400"] ?? null;
  const pop800 = coverage.population?.by_buffer_m["800"] ?? null;

  return (
    <div className="page">
      <h1>Stop Accessibility &amp; Coverage</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Walk-buffer coverage around stops (~5 min / ~10 min walk), weighted by US Census
        block-group population where available.
      </p>

      <div className="kpi-row" style={{ marginBottom: "1rem" }}>
        <div className="kpi-tile">
          <div className="kpi-tile__label">Total county population</div>
          <div className="kpi-tile__value">
            {coverage.population ? coverage.population.total_population.toLocaleString() : "—"}
          </div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-tile__label">Covered within 400m (~5 min walk)</div>
          <div className="kpi-tile__value">{pct(pop400?.pct_of_total_population ?? null)}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-tile__label">Covered within 800m (~10 min walk)</div>
          <div className="kpi-tile__value">{pct(pop800?.pct_of_total_population ?? null)}</div>
        </div>
      </div>

      {!coverage.population && (
        <div className="card" style={{ color: "var(--text-muted)" }}>
          Population-weighted stats aren't available for this feed (no Census API key
          configured, or the region isn't covered). Buffer areas below are still accurate.
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <CoverageMap feed={selectedFeed} coverage={coverage} />
      </div>
    </div>
  );
}
