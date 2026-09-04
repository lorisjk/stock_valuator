/**
 * The growth chart's mode control: year-over-year against quarter-over-quarter.
 *
 * **One control for the whole chart, not one per panel.** The mode is a property
 * of the measurement, not of the concept -- `calculate_growth` takes the same
 * `periods` for every one of the 39 -- so a per-panel control would be 39 copies
 * of one boolean, and a chart whose panels were half YoY and half QoQ would be
 * unreadable as a chart. It is also the shape the data has: `facts_growth` holds
 * two columns over one row set, so a global switch reads a different array and a
 * per-panel switch would read a different array *per panel* to no end.
 *
 * Radios rather than a checkbox. A checkbox has a default state and an
 * exceptional one, and QoQ is not an exception to YoY -- both are ordinary ways
 * to read the same series. The reading order is the reference's for every other
 * control on these tabs (`OutlierControls`): control, then the caption that says
 * what it means.
 *
 * **The caption is the point of the control, not decoration.** It carries the
 * one finding a first-time reader needs -- QoQ is not seasonally adjusted -- and
 * it is stated where the mode is chosen rather than only in the encyclopedia,
 * because a regular sawtooth read as noise is the failure this text exists to
 * prevent. The text comes off the registry (`config.GROWTH_MODES`), so the
 * caption, the mechanism note and the pipeline cannot say different things.
 */
import ReactMarkdown from "react-markdown";
import type { GrowthMode } from "./contracts.ts";
import "./growth-mode.css";

export default function GrowthModeControl({
  modes,
  mode,
  onMode,
}: {
  /** `registry.charts.growth.modes`, in declaration order. */
  modes: readonly GrowthMode[];
  /** The selected mode's key. */
  mode: string;
  onMode: (next: string) => void;
}) {
  // A single mode is a statement, not a choice: an older registry declaring one
  // column should draw the chart without a control offering nothing.
  if (modes.length < 2) return null;
  const current = modes.find((m) => m.key === mode) ?? modes[0];

  return (
    <div className="growth-mode">
      {/* `role="radiogroup"` over a `<div>` rather than a `<fieldset>`: a
          fieldset's `<legend>` is laid out specially and does not participate in
          its parent's flex box consistently across browsers, so the label would
          sit on its own line in some and not others. The grouping and the
          accessible name are identical either way. */}
      <div className="growth-mode__set" role="radiogroup" aria-labelledby="growth-mode-legend">
        <span className="growth-mode__legend" id="growth-mode-legend">
          Growth measured
        </span>
        {modes.map((m) => (
          <label className="growth-mode__option" key={m.key}>
            <input
              type="radio"
              name="growth-mode"
              value={m.key}
              checked={m.key === current.key}
              onChange={() => onMode(m.key)}
            />{" "}
            {m.label} <span className="growth-mode__short">({m.short})</span>
          </label>
        ))}
      </div>

      {/* Markdown because the registry's text is markdown -- QoQ's carries the
          bolded "Not seasonally adjusted", which is the half of the sentence a
          reader skimming has to catch. `p` unwrapped so the caption stays one
          line in the flow rather than a block with its own margins. */}
      <p className="caption growth-mode__note">
        <ReactMarkdown components={{ p: ({ children }) => <>{children}</> }}>
          {current.description}
        </ReactMarkdown>
      </p>
    </div>
  );
}
