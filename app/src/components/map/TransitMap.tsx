import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import { assetUrl } from "../../lib/manifest";
import { ensurePmtilesProtocol } from "../../lib/pmtiles";
import type { FeedEntry } from "../../types/dataContract";

const BASEMAP_STYLE = {
  version: 8 as const,
  sources: {
    "carto-light": {
      type: "raster" as const,
      tiles: [
        "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      ],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
  layers: [{ id: "carto-light", type: "raster" as const, source: "carto-light" }],
};

function addFeedLayers(map: maplibregl.Map, feed: FeedEntry) {
  for (const id of ["routes-line", "stops-circle"]) {
    if (map.getLayer(id)) map.removeLayer(id);
  }
  for (const id of ["routes", "stops"]) {
    if (map.getSource(id)) map.removeSource(id);
  }

  if (feed.assets.tiles) {
    map.addSource("routes", { type: "vector", url: `pmtiles://${assetUrl(feed.assets.tiles)}` });
    map.addSource("stops", { type: "vector", url: `pmtiles://${assetUrl(feed.assets.tiles)}` });
    map.addLayer({
      id: "routes-line",
      type: "line",
      source: "routes",
      "source-layer": "routes",
      paint: { "line-color": ["coalesce", ["get", "route_color"], "#2457c5"], "line-width": 2 },
    });
    map.addLayer({
      id: "stops-circle",
      type: "circle",
      source: "stops",
      "source-layer": "stops",
      minzoom: 11,
      paint: { "circle-radius": 3, "circle-color": "#1a1d21", "circle-opacity": 0.7 },
    });
  } else {
    // Fallback for feeds/dev environments without tippecanoe: load raw GeoJSON directly.
    map.addSource("routes", { type: "geojson", data: assetUrl(feed.assets.routes_geojson) });
    map.addSource("stops", { type: "geojson", data: assetUrl(feed.assets.stops_geojson) });
    map.addLayer({
      id: "routes-line",
      type: "line",
      source: "routes",
      paint: { "line-color": ["coalesce", ["get", "route_color"], "#2457c5"], "line-width": 2 },
    });
    map.addLayer({
      id: "stops-circle",
      type: "circle",
      source: "stops",
      minzoom: 11,
      paint: { "circle-radius": 3, "circle-color": "#1a1d21", "circle-opacity": 0.7 },
    });
  }

  map.fitBounds(
    [
      [feed.bbox[0], feed.bbox[1]],
      [feed.bbox[2], feed.bbox[3]],
    ],
    { padding: 32, animate: false },
  );
}

export default function TransitMap({ feed }: { feed: FeedEntry | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    ensurePmtilesProtocol();
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: [-80.2, 26.1],
      zoom: 9,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = map;
    return () => map.remove();
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !feed) return;
    if (map.isStyleLoaded()) {
      addFeedLayers(map, feed);
    } else {
      map.once("load", () => addFeedLayers(map, feed));
    }
  }, [feed]);

  return <div ref={containerRef} className="map-container" />;
}
