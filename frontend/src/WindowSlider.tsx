/**
 * The trailing-window control: `st.slider("Window (years)", 1, 15, default)`.
 *
 * **This is a rebuild, not a restyle.** `_window_frame` runs before anything
 * else in every builder, and the "No Data" rule is evaluated *after* it, so
 * moving this changes which panels are blank, which changes the panel count,
 * which changes the grid `makeGrid` derives from it. A finished figure cannot
 * be re-tiled (inventory 4.1). The valuation chart's mean line moves with it
 * too, because `build_valuation` computes the mean over the windowed series.
 *
 * Not debounced. Measured on the widest real case -- a 13-panel fundamentals
 * chart, which is the most any profile offers -- one rebuild from the raw
 * series is well inside a frame, so a debounce would add latency to hide a cost
 * that is not there. The number is in the report; if a later item makes the
 * build materially heavier, that measurement is the thing to re-take.
 *
 * `onChange` fires per input event rather than on release: `<input type=range>`
 * fires `input` continuously while dragging and `change` on release, and React
 * maps `onChange` to the former. That is deliberate -- the chart tracks the
 * handle -- and it is the reason the cost above was worth measuring.
 */
import type { ChartId } from "./contracts.ts";
import { DEFAULT_YEARS, YEARS_MAX, YEARS_MIN } from "./charts/defaults.ts";

export default function WindowSlider({
  chart,
  years,
  onChange,
}: {
  chart: ChartId;
  years: number;
  onChange: (next: number) => void;
}) {
  const isDefault = years === DEFAULT_YEARS[chart];
  return (
    <p style={{ display: "flex", alignItems: "center", gap: "0.6rem", margin: "0.6rem 0" }}>
      <label htmlFor={`years-${chart}`} style={{ whiteSpace: "nowrap" }}>
        Window (years)
      </label>
      <input
        id={`years-${chart}`}
        type="range"
        min={YEARS_MIN}
        max={YEARS_MAX}
        step={1}
        value={years}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: "0 1 16rem" }}
      />
      <output htmlFor={`years-${chart}`} style={{ minWidth: "2.5rem" }}>
        <strong>{years}</strong>
      </output>
      <button type="button" onClick={() => onChange(DEFAULT_YEARS[chart])} disabled={isDefault}>
        Default ({DEFAULT_YEARS[chart]})
      </button>
    </p>
  );
}
