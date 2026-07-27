import type { Manifest } from "../types/dataContract";

// All generated data lives under <base>/data/... — see docs/data-contract.md.
// Using import.meta.env.BASE_URL (not a hardcoded "/") keeps this working
// whether the app is served at a domain root or a GitHub Pages project path.
const DATA_ROOT = `${import.meta.env.BASE_URL}data`;

let manifestPromise: Promise<Manifest> | null = null;

export function fetchManifest(): Promise<Manifest> {
  if (!manifestPromise) {
    manifestPromise = fetch(`${DATA_ROOT}/manifest.json`).then((res) => {
      if (!res.ok) throw new Error(`Failed to load manifest.json: ${res.status}`);
      return res.json() as Promise<Manifest>;
    });
  }
  return manifestPromise;
}

export function assetUrl(path: string): string {
  // Asset paths in the manifest are already relative to the repo root
  // (e.g. "data/broward-bct/headway.json"); resolve them against BASE_URL.
  return `${import.meta.env.BASE_URL}${path}`;
}

export async function fetchJsonAsset<T>(path: string): Promise<T> {
  const res = await fetch(assetUrl(path));
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

/** comparison.json lives at the build root (data/comparison.json), not under a
 * per-feed directory, since it summarizes across all feeds in the manifest. */
export function fetchComparison<T>(): Promise<T> {
  return fetchJsonAsset<T>("data/comparison.json");
}
