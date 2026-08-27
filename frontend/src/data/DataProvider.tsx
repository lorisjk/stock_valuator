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
import type { ConceptCandidates, Frame, Frames, Meta, Registry } from "../contracts.ts";
import { DataContext, type DataContextValue, type UniverseEntry } from "./DataContext.ts";
import {
  fetchCandidates,
  fetchMeta,
  fetchNotice,
  fetchRegistry,
  fetchTickerFacts,
  fetchTickerFrames,
} from "./load.ts";

export function DataProvider({ children }: { children: ReactNode }) {
  const [registry, setRegistry] = useState<Registry | null>(null);
  const [universe, setUniverse] = useState<UniverseEntry[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const cache = useRef(new Map<string, Promise<Frames>>());
  // Same policy as `cache`, one per file. `facts_full` is the bigger of the two
  // (21 kB gzipped against 14 kB) and no chart tab needs it, so it is kept in
  // its own map rather than merged into a ticker's core frames -- a merged
  // cache would have to fetch both to answer for either.
  const factsCache = useRef(new Map<string, Promise<Frame>>());
  const candidatesCache = useRef<Promise<ConceptCandidates> | null>(null);

  useEffect(() => {
    let live = true;
    Promise.all([
      fetchRegistry(),
      fetch("/universe.json").then((r) => {
        if (!r.ok) throw new Error(`/universe.json -- ${r.status} ${r.statusText}`);
        return r.json() as Promise<UniverseEntry[]>;
      }),
      // Neither of these can fail the app. `meta.json` feeds one caption and the
      // notice is allowed to be absent, so both resolve to null rather than
      // rejecting -- putting them in the same Promise.all as the two contracts
      // and letting them throw would turn a missing caption into a guard screen.
      fetchMeta().catch(() => null),
      fetchNotice().catch(() => null),
    ])
      .then(([loadedRegistry, loadedUniverse, loadedMeta, loadedNotice]) => {
        if (!live) return;
        setRegistry(loadedRegistry);
        setUniverse(loadedUniverse);
        setMeta(loadedMeta);
        setNotice(loadedNotice);
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

  const factsFor = useCallback((ticker: string) => {
    const pending = factsCache.current.get(ticker);
    if (pending) return pending;
    const request = fetchTickerFacts(ticker).catch((e: unknown) => {
      factsCache.current.delete(ticker);
      throw e;
    });
    factsCache.current.set(ticker, request);
    return request;
  }, []);

  // Ticker-independent, so one slot rather than a map: it is the same 7.8 kB
  // for every ticker and it changes only when config.py does.
  const candidatesFile = useCallback(() => {
    if (candidatesCache.current) return candidatesCache.current;
    const request = fetchCandidates().catch((e: unknown) => {
      candidatesCache.current = null;
      throw e;
    });
    candidatesCache.current = request;
    return request;
  }, []);

  const value = useMemo<DataContextValue>(
    () => ({
      registry,
      meta,
      notice,
      universe,
      error,
      loading: !registry && !error,
      framesFor,
      factsFor,
      candidatesFile,
    }),
    [registry, meta, notice, universe, error, framesFor, factsFor, candidatesFile],
  );
  return <DataContext value={value}>{children}</DataContext>;
}
