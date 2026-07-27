import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { CoverageData, FeedEntry } from "../../types/dataContract";

const STYLE = {
  version: 8 as const,
  sources: {
    "carto-light": {
      type: "raster" as const,
      tiles: ["https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors © CARTO",
    },
  },
  layers: [{ id: "carto-light", type: "raster" as const, source: "carto-light" }],
};

export default function CoverageMap({
  feed,
  coverage,
}: {
  feed: FeedEntry;
  coverage: CoverageData;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE,
      center: [(feed.bbox[0] + feed.bbox[2]) / 2, (feed.bbox[1] + feed.bbox[3]) / 2],
      zoom: 9,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      const buffer800 = coverage.buffers_geojson["800"];
      const buffer400 = coverage.buffers_geojson["400"];
      if (buffer800) {
        map.addSource("buffer-800", { type: "geojson", data: buffer800 as GeoJSON.GeoJSON });
        map.addLayer({
          id: "buffer-800-fill",
          type: "fill",
          source: "buffer-800",
          paint: { "fill-color": "#2a78d6", "fill-opacity": 0.12 },
        });
      }
      if (buffer400) {
        map.addSource("buffer-400", { type: "geojson", data: buffer400 as GeoJSON.GeoJSON });
        map.addLayer({
          id: "buffer-400-fill",
          type: "fill",
          source: "buffer-400",
          paint: { "fill-color": "#2a78d6", "fill-opacity": 0.28 },
        });
      }
      map.fitBounds(
        [
          [feed.bbox[0], feed.bbox[1]],
          [feed.bbox[2], feed.bbox[3]],
        ],
        { padding: 24, animate: false },
      );
    });

    return () => map.remove();
  }, [feed, coverage]);

  return <div ref={containerRef} className="map-container" style={{ minHeight: 360 }} />;
}
