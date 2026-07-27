import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { FeedEntry, Manifest } from "../types/dataContract";
import { fetchManifest } from "./manifest";

interface FeedContextValue {
  manifest: Manifest | null;
  loading: boolean;
  error: string | null;
  selectedFeedId: string | null;
  setSelectedFeedId: (id: string) => void;
  selectedFeed: FeedEntry | null;
}

const FeedContext = createContext<FeedContextValue | null>(null);

export function FeedProvider({ children }: { children: ReactNode }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFeedId, setSelectedFeedId] = useState<string | null>(null);

  useEffect(() => {
    fetchManifest()
      .then((m) => {
        setManifest(m);
        if (m.feeds.length > 0) setSelectedFeedId(m.feeds[0].id);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  const selectedFeed = useMemo(
    () => manifest?.feeds.find((f) => f.id === selectedFeedId) ?? null,
    [manifest, selectedFeedId],
  );

  return (
    <FeedContext.Provider
      value={{ manifest, loading, error, selectedFeedId, setSelectedFeedId, selectedFeed }}
    >
      {children}
    </FeedContext.Provider>
  );
}

export function useFeedContext(): FeedContextValue {
  const ctx = useContext(FeedContext);
  if (!ctx) throw new Error("useFeedContext must be used within a FeedProvider");
  return ctx;
}
