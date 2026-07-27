import maplibregl from "maplibre-gl";
import { Protocol } from "pmtiles";

let registered = false;

// Idempotent: React StrictMode / hot reload can call this more than once.
export function ensurePmtilesProtocol(): void {
  if (registered) return;
  const protocol = new Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  registered = true;
}
