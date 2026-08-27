/**
 * The shared-data context and the hooks that read it.
 *
 * Split out of DataProvider.tsx only because a file that exports both a
 * component and a hook breaks react-refresh. The reasoning for what lives here
 * is in DataProvider.tsx.
 */
import { createContext, useContext, useEffect, useState } from "react";
import type { ConceptCandidates, Frame, Frames, Meta, Registry } from "../contracts.ts";
import { candidatesFor } from "./load.ts";

export interface UniverseEntry {
  ticker: string;
  profile: string;
}

export interface DataContextValue {
  registry: Registry | null;
  /** Run provenance for the freshness block. Never fatal -- see META_SCHEMA. */
  meta: Meta | null;
  /** The update notice's raw markdown; null when there is none to show. */
  notice: string | null;
  universe: UniverseEntry[];
  /** The registry/universe load: an Error when it failed, else null. */
  error: Error | null;
  loading: boolean;
  /** Cached per ticker. Repeat calls share one request. */
  framesFor: (ticker: string) => Promise<Frames>;
  /** A ticker's `facts_full` slice, from the second per-ticker file. */
  factsFor: (ticker: string) => Promise<Frame>;
  /** `concept_candidates.json`, fetched once on first use and held. */
  candidatesFile: () => Promise<ConceptCandidates>;
}

export const DataContext = createContext<DataContextValue | null>(null);

export function useData(): DataContextValue {
  const value = useContext(DataContext);
  if (!value) throw new Error("useData must be used inside <DataProvider>");
  return value;
}

interface Loaded {
  ticker: string;
  frames: Frames | null;
  error: Error | null;
}

/**
 * One ticker's frames, with the load state a component needs to render.
 *
 * The result carries the ticker it belongs to, and a result for a different
 * ticker is reported as "still loading". That is what keeps the previous
 * ticker's chart from being shown for a moment under the new ticker's name --
 * and it means the effect never calls setState synchronously, so switching
 * tickers costs one render rather than a cascade.
 */
export function useTickerFrames(ticker: string): { frames: Frames | null; error: Error | null } {
  const { framesFor } = useData();
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let live = true;
    framesFor(ticker)
      .then((frames) => {
        if (live) setLoaded({ ticker, frames, error: null });
      })
      .catch((e: unknown) => {
        if (live) {
          setLoaded({ ticker, frames: null, error: e instanceof Error ? e : new Error(String(e)) });
        }
      });
    return () => {
      live = false;
    };
  }, [ticker, framesFor]);

  if (loaded?.ticker !== ticker) return { frames: null, error: null };
  return { frames: loaded.frames, error: loaded.error };
}

interface LoadedFacts {
  ticker: string;
  frame: Frame | null;
  error: Error | null;
}

/**
 * One ticker's `facts_full` slice, with the same stale-result rule
 * `useTickerFrames` uses: a result for a different ticker reads as "still
 * loading", so the previous company's facts are never shown under the new
 * company's name.
 */
export function useTickerFacts(ticker: string): { facts: Frame | null; error: Error | null } {
  const { factsFor } = useData();
  const [loaded, setLoaded] = useState<LoadedFacts | null>(null);

  useEffect(() => {
    let live = true;
    factsFor(ticker)
      .then((frame) => {
        if (live) setLoaded({ ticker, frame, error: null });
      })
      .catch((e: unknown) => {
        if (live) {
          setLoaded({ ticker, frame: null, error: e instanceof Error ? e : new Error(String(e)) });
        }
      });
    return () => {
      live = false;
    };
  }, [ticker, factsFor]);

  if (loaded?.ticker !== ticker) return { facts: null, error: null };
  return { facts: loaded.frame, error: loaded.error };
}

/**
 * `get_concept_candidates(ticker)`'s keys, for the raw-versus-derived split.
 *
 * `null` while the file is in flight, and `null` if it failed. The caller shows
 * the facts table without the split rather than refusing to draw it: the
 * numbers are the section's point, and the split is an annotation on top of
 * them. That is deliberately unlike a missing `registry.json`, which decides
 * what a chart is even allowed to show.
 */
export function useConceptCandidates(ticker: string): {
  candidates: Set<string> | null;
  error: Error | null;
} {
  const { candidatesFile } = useData();
  const [file, setFile] = useState<ConceptCandidates | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let live = true;
    candidatesFile()
      .then((loaded) => {
        if (live) setFile(loaded);
      })
      .catch((e: unknown) => {
        if (live) setError(e instanceof Error ? e : new Error(String(e)));
      });
    return () => {
      live = false;
    };
  }, [candidatesFile]);

  return { candidates: file ? candidatesFor(file, ticker) : null, error };
}
