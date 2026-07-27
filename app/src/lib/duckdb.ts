// Lazy-loaded duckdb-wasm for the ad hoc "explore" panel. Only imported/
// instantiated when a user actually opens that panel — the map/dashboard
// pages never pay for the wasm bundle.
import * as duckdb from "@duckdb/duckdb-wasm";

let dbPromise: Promise<duckdb.AsyncDuckDB> | null = null;

async function getDb(): Promise<duckdb.AsyncDuckDB> {
  if (!dbPromise) {
    dbPromise = (async () => {
      const bundles = duckdb.getJsDelivrBundles();
      const bundle = await duckdb.selectBundle(bundles);
      const workerUrl = URL.createObjectURL(
        new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }),
      );
      const worker = new Worker(workerUrl);
      const logger = new duckdb.VoidLogger();
      const db = new duckdb.AsyncDuckDB(logger, worker);
      await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
      URL.revokeObjectURL(workerUrl);
      return db;
    })();
  }
  return dbPromise;
}

export async function queryParquetUrl(
  parquetUrl: string,
  sql: string,
): Promise<Record<string, unknown>[]> {
  const db = await getDb();
  await db.registerFileURL(
    "stop_times.parquet",
    parquetUrl,
    duckdb.DuckDBDataProtocol.HTTP,
    false,
  );
  const conn = await db.connect();
  try {
    const result = await conn.query(sql);
    return result.toArray().map((row) => row.toJSON() as Record<string, unknown>);
  } finally {
    await conn.close();
  }
}
