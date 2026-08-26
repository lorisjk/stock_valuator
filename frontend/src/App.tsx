import { useState } from "react";
import ChartView from "./ChartView.tsx";
import type { ChartId } from "./contracts.ts";
import { useData } from "./data/DataContext.ts";
import { DataProvider } from "./data/DataProvider.tsx";

// Every chart is now built from the raw series -- items 4, 5 and 6 -- so the
// `REBUILT` list and the pre-rendered fallback behind it are both gone. The
// fallback only ever had figures for AAPL and MSFT; keeping it would have meant
// one path that works for 609 tickers and one that works for two. `Chart.tsx`
// and the six `public/*_{chart}.json` files it read are now unreferenced.
// Which chart ids are actually built is stated once, in ChartView's BUILDERS.

function Workspace() {
  const { registry, universe, error, loading } = useData();
  const [ticker, setTicker] = useState("AAPL");
  const [type, setType] = useState<ChartId>("valuation");

  if (error) return <p role="alert">Could not load the export: {error.message}</p>;
  if (loading || !registry) return <p>Loading the registry…</p>;

  const profile = registry.ticker_profile[ticker] ?? registry.default_profile;

  return (
    <>
      <h1>Stock Valuation</h1>
      <p>
        <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
          {universe.map((entry) => (
            <option key={entry.ticker} value={entry.ticker}>
              {entry.ticker} — {entry.profile}
            </option>
          ))}
        </select>{" "}
        <select value={type} onChange={(e) => setType(e.target.value as ChartId)}>
          <option value="valuation">Valuation</option>
          <option value="fundamentals">Fundamentals</option>
          <option value="growth">Growth</option>
        </select>{" "}
        <span>
          {ticker} · profile <code>{profile}</code>
        </span>
      </p>

      <ChartView registry={registry} ticker={ticker} chart={type} />
    </>
  );
}

export default function App() {
  return (
    <DataProvider>
      <Workspace />
    </DataProvider>
  );
}
