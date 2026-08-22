import { useState } from "react";
import Chart from "./Chart";
import ValuationChart from "./ValuationChart.tsx";
import { useData } from "./data/DataContext.ts";
import { DataProvider } from "./data/DataProvider.tsx";

type ChartType = "valuation" | "fundamentals" | "growth";

function Workspace() {
  const { registry, universe, error, loading } = useData();
  const [ticker, setTicker] = useState("AAPL");
  const [type, setType] = useState<ChartType>("valuation");

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
        <select value={type} onChange={(e) => setType(e.target.value as ChartType)}>
          <option value="valuation">Valuation</option>
          <option value="fundamentals">Fundamentals</option>
          <option value="growth">Growth</option>
        </select>{" "}
        <span>
          {ticker} · profile <code>{profile}</code>
        </span>
      </p>

      {type === "valuation" ? (
        <ValuationChart registry={registry} ticker={ticker} />
      ) : (
        // Items 5 and 6. Until those are built these two tabs keep loading the
        // pre-rendered figure the scaffold shipped -- it only exists for AAPL
        // and MSFT, which is why it says so rather than failing silently.
        <>
          <p>
            <em>
              Not rebuilt yet (rebuild list items 5 and 6). Showing the pre-rendered figure, which
              exists for AAPL and MSFT only.
            </em>
          </p>
          <Chart ticker={ticker} type={type} />
        </>
      )}
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
