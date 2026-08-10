import { useState } from "react";
import DispatchConsole from "../components/agent/DispatchConsole";
import ExplorePanel from "../components/charts/ExplorePanel";
import TransitMap from "../components/map/TransitMap";
import { useFeedContext } from "../lib/FeedContext";
import type { MapPoint } from "../types/agent";

export default function MapExplorer() {
  const { selectedFeed, loading, error } = useFeedContext();
  const [highlight, setHighlight] = useState<MapPoint[]>([]);

  if (loading) return <div className="page empty-state">Loading feed manifest…</div>;
  if (error) return <div className="page empty-state">Couldn't load data: {error}</div>;
  if (!selectedFeed) return <div className="page empty-state">No feed selected.</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
        <TransitMap feed={selectedFeed} highlight={highlight} />
        <DispatchConsole feedId={selectedFeed.id} onMapHighlight={setHighlight} />
      </div>
      {selectedFeed.assets.stop_times_parquet && (
        <div style={{ padding: "0 1.25rem 1.25rem" }}>
          <ExplorePanel parquetPath={selectedFeed.assets.stop_times_parquet} />
        </div>
      )}
    </div>
  );
}
