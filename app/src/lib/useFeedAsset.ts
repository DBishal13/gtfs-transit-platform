import { useEffect, useState } from "react";
import { fetchJsonAsset } from "./manifest";

interface AssetState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/** Fetches a per-feed JSON asset (e.g. feed.assets.headway) whenever the path changes. */
export function useFeedAsset<T>(path: string | null | undefined): AssetState<T> {
  const [state, setState] = useState<AssetState<T>>({ data: null, loading: true, error: null });

  useEffect(() => {
    if (!path) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    fetchJsonAsset<T>(path)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (!cancelled) setState({ data: null, loading: false, error: String(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [path]);

  return state;
}
