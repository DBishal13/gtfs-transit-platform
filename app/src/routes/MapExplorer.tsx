import ExplorePanel from "../components/charts/ExplorePanel";
import TransitMap from "../components/map/TransitMap";
import { useFeedContext } from "../lib/FeedContext";

export default function MapExplorer() {
  const { selectedFeed, loading, error } = useFeedContext();

  if (loading) return <div className="page empty-state">Loading feed manifest…</div>;
  if (error) return <div className="page empty-state">Couldn't load data: {error}</div>;
  if (!selectedFeed) return <div className="page empty-state">No feed selected.</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <TransitMap feed={selectedFeed} />
      </div>
      {selectedFeed.assets.stop_times_parquet && (
        <div style={{ padding: "0 1.25rem 1.25rem" }}>
          <ExplorePanel parquetPath={selectedFeed.assets.stop_times_parquet} />
        </div>
      )}
    </div>
  );
}
