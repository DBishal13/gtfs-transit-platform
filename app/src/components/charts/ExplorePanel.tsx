import { useState } from "react";
import { assetUrl } from "../../lib/manifest";

const DEFAULT_SQL = `select route_id, count(*) as departures
from read_parquet('stop_times.parquet')
group by route_id
order by departures desc
limit 20`;

/** Ad hoc SQL against the feed's stop_times Parquet extract, via duckdb-wasm.
 * duckdb-wasm itself is only imported when a user opens this panel and hits Run,
 * so the map/dashboard pages never pay for the wasm bundle. */
export default function ExplorePanel({ parquetPath }: { parquetPath: string }) {
  const [open, setOpen] = useState(false);
  const [sql, setSql] = useState(DEFAULT_SQL);
  const [rows, setRows] = useState<Record<string, unknown>[] | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const { queryParquetUrl } = await import("../../lib/duckdb");
      const result = await queryParquetUrl(assetUrl(parquetPath), sql);
      setRows(result);
    } catch (err) {
      setError(String(err));
    } finally {
      setRunning(false);
    }
  }

  if (!open) {
    return (
      <button className="card" onClick={() => setOpen(true)} style={{ cursor: "pointer" }}>
        Open ad hoc SQL explorer (runs in your browser via duckdb-wasm)
      </button>
    );
  }

  return (
    <div className="card">
      <h3>Ad hoc SQL explorer</h3>
      <p style={{ color: "var(--text-muted)" }}>
        Queries this feed's stop_times Parquet extract entirely in your browser (duckdb-wasm) —
        nothing is sent to a server.
      </p>
      <textarea
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        rows={5}
        style={{
          width: "100%",
          fontFamily: "monospace",
          background: "var(--bg)",
          color: "var(--text)",
          border: "1px solid var(--border)",
          borderRadius: 6,
          padding: "0.5rem",
        }}
      />
      <div style={{ marginTop: "0.5rem" }}>
        <button onClick={run} disabled={running}>
          {running ? "Running…" : "Run query"}
        </button>
      </div>
      {error && <p style={{ color: "var(--error)" }}>{error}</p>}
      {rows && rows.length > 0 && (
        <table style={{ marginTop: "0.75rem" }}>
          <thead>
            <tr>
              {Object.keys(rows[0]).map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {Object.values(row).map((v, j) => (
                  <td key={j}>{String(v)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
