/**
 * The shared-data context and the hooks that read it.
 *
 * Split out of DataProvider.tsx only because a file that exports both a
 * component and a hook breaks react-refresh. The reasoning for what lives here
 * is in DataProvider.tsx.
 */
import { createContext, useContext, useEffect, useState } from "react";
import type { Frames, Registry } from "../contracts.ts";

export interface UniverseEntry {
  ticker: string;
  profile: string;
}

export interface DataContextValue {
  registry: Registry | null;
  universe: UniverseEntry[];
  /** The registry/universe load: an Error when it failed, else null. */
  error: Error | null;
  loading: boolean;
  /** Cached per ticker. Repeat calls share one request. */
  framesFor: (ticker: string) => Promise<Frames>;
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
