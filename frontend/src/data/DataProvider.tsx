/**
 * One place that owns the two contracts, so nothing refetches them.
 *
 * The registry is needed by every view -- pickers, axis labels, reference
 * lines, percent formatting, the encyclopedia -- and it is 11 kB gzipped and
 * changes only when config.py does. Fetching it once at mount and holding it is
 * the whole design.
 *
 * A ticker's frames are needed by four chart tabs and the data tab. Fetching
 * them per component would refetch 14 kB on every tab switch, so they are held
 * in a keyed cache here. The cache is unbounded on purpose: a ticker's core
 * file is 14 kB gzipped and a session touches a handful, so an eviction policy
 * would be more code than the thing it manages.
 *
 * What this provider deliberately does **not** hold: anything a chart derives.
 * No figures, no selections, no window. A cached figure would outlive the
 * widget state that produced it -- app.py:92 says exactly this, and it is why
 * the Streamlit app caches frames and never figures.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Frames, Registry } from "../contracts.ts";
import { DataContext, type DataContextValue, type UniverseEntry } from "./DataContext.ts";
import { fetchRegistry, fetchTickerFrames } from "./load.ts";

export function DataProvider({ children }: { children: ReactNode }) {
  const [registry, setRegistry] = useState<Registry | null>(null);
  const [universe, setUniverse] = useState<UniverseEntry[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const cache = useRef(new Map<string, Promise<Frames>>());

  useEffect(() => {
    let live = true;
    Promise.all([
      fetchRegistry(),
      fetch("/universe.json").then((r) => {
        if (!r.ok) throw new Error(`/universe.json -- ${r.status} ${r.statusText}`);
        return r.json() as Promise<UniverseEntry[]>;
      }),
    ])
      .then(([loadedRegistry, loadedUniverse]) => {
        if (!live) return;
        setRegistry(loadedRegistry);
        setUniverse(loadedUniverse);
      })
      .catch((e: unknown) => {
        if (live) setError(e instanceof Error ? e : new Error(String(e)));
      });
    return () => {
      live = false;
    };
  }, []);

  // The promise is cached, not the result, so two components asking for the
  // same ticker in the same tick share one request instead of racing.
  const framesFor = useCallback((ticker: string) => {
    const pending = cache.current.get(ticker);
    if (pending) return pending;
    const request = fetchTickerFrames(ticker).catch((e: unknown) => {
      cache.current.delete(ticker); // a failure must not be cached as an answer
      throw e;
    });
    cache.current.set(ticker, request);
    return request;
  }, []);

  const value = useMemo<DataContextValue>(
    () => ({ registry, universe, error, loading: !registry && !error, framesFor }),
    [registry, universe, error, framesFor],
  );
  return <DataContext value={value}>{children}</DataContext>;
}
