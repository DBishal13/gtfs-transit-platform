import { useFeedContext } from "../lib/FeedContext";
import { useFeedAsset } from "../lib/useFeedAsset";
import type { QualityReport } from "../types/dataContract";

function StatusBadge({ status }: { status: "pass" | "warn" | "fail" }) {
  return <span className={`badge badge--${status}`}>{status.toUpperCase()}</span>;
}

export default function DataQuality() {
  const { selectedFeed } = useFeedContext();
  const { data: report, loading, error } = useFeedAsset<QualityReport>(
    selectedFeed?.assets.quality,
  );

  if (loading) return <div className="page empty-state">Loading quality report…</div>;
  if (error) return <div className="page empty-state">Couldn't load quality report: {error}</div>;
  if (!report) return <div className="page empty-state">No data.</div>;

  return (
    <div className="page">
      <h1>Data Quality</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Referential-integrity and sanity checks run against this feed, merged with
        MobilityData's official gtfs-validator when available.
      </p>

      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <StatusBadge status={report.summary.status} />
          <span>
            {report.summary.custom_errors + report.summary.official_errors} error(s),{" "}
            {report.summary.custom_warnings} warning(s)
          </span>
        </div>
        <p style={{ color: "var(--text-muted)", marginBottom: 0 }}>
          Official gtfs-validator: {report.official_validator.ran ? "ran" : "not run for this build"}
        </p>
      </div>

      <div className="card">
        <h3>Custom checks</h3>
        {report.custom_checks.length === 0 ? (
          <div className="empty-state">No issues found — this feed passed every check.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Check</th>
                <th>Severity</th>
                <th>Message</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {report.custom_checks.map((f) => (
                <tr key={f.check}>
                  <td>{f.check}</td>
                  <td>
                    <span className={`badge badge--${f.severity === "error" ? "fail" : "warn"}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td>{f.message}</td>
                  <td>{f.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {report.official_validator.notice_types.length > 0 && (
        <div className="card">
          <h3>Official validator notices</h3>
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Severity</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {report.official_validator.notice_types.map((n, i) => (
                <tr key={i}>
                  <td>{n.code}</td>
                  <td>{n.severity}</td>
                  <td>{n.total_notices}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
