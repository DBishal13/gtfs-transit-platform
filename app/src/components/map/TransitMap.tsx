import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import { assetUrl } from "../../lib/manifest";
import { ensurePmtilesProtocol } from "../../lib/pmtiles";
import type { MapPoint } from "../../types/agent";
import type { FeedEntry } from "../../types/dataContract";

const HIGHLIGHT_SOURCE_ID = "dispatch-highlight";

function pointsToGeoJSON(points: MapPoint[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: points.map((p) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [p.lon, p.lat] },
      properties: { label: p.label ?? "" },
    })),
  };
}

/** Renders Dispatch console results (nearest stops, a geocoded point, reachable stops)
 * as a distinct halo+dot layer, separate from the base routes/stops layers, and pans the
 * map to fit them so a result is visible without the rider manually panning. */
function setHighlightLayer(map: maplibregl.Map, points: MapPoint[]) {
  const data = pointsToGeoJSON(points);
  const source = map.getSource(HIGHLIGHT_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(data);
  } else {
    map.addSource(HIGHLIGHT_SOURCE_ID, { type: "geojson", data });
    map.addLayer({
      id: "dispatch-highlight-halo",
      type: "circle",
      source: HIGHLIGHT_SOURCE_ID,
      paint: { "circle-radius": 12, "circle-color": "#eb6834", "circle-opacity": 0.25 },
    });
    map.addLayer({
      id: "dispatch-highlight-point",
      type: "circle",
      source: HIGHLIGHT_SOURCE_ID,
      paint: {
        "circle-radius": 5,
        "circle-color": "#eb6834",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
  }

  if (points.length > 0) {
    const bounds = points.reduce(
      (b, p) => b.extend([p.lon, p.lat] as [number, number]),
      new maplibregl.LngLatBounds([points[0].lon, points[0].lat], [points[0].lon, points[0].lat]),
    );
    map.fitBounds(bounds, { padding: 80, maxZoom: 16, duration: 600 });
  }
}

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

export default function TransitMap({
  feed,
  highlight,
}: {
  feed: FeedEntry | null;
  highlight?: MapPoint[];
}) {
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

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const points = highlight ?? [];
    const apply = () => setHighlightLayer(map, points);
    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [highlight]);

  return <div ref={containerRef} className="map-container" />;
}
