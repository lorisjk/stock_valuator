/**
 * The metric picker: one checkbox per id the ticker's profile offers.
 *
 * **The options are the narrowed catalogue and nothing else.** `offerable`
 * comes from `selectMetricIds(registry, chart, ticker, null)` -- the same
 * function every builder calls -- so a metric `profile_visibility` hides is
 * never rendered as an option. The builders narrow again on their own, which
 * makes a stale selection silently correct rather than an error; this control
 * exists so the user never sees a checkbox that would quietly do nothing.
 *
 * **Label first, id second.** Streamlit passes `format_func=lambda i: labels[i]`,
 * so the reference shows labels, and the labels are the readable half:
 * "Shares Outstanding (Stock Dilution/Repurchase)" against `SharesOutstanding`,
 * "P/E (TTM)" against `pe_ratio`. But the *panel titles* are ids (item 4's
 * finding) while the y-axes carry labels, so a picker showing only labels
 * leaves nothing connecting a checkbox to the panel it produces. Showing both
 * makes this the one place the two names are visible together.
 *
 * **Catalogue order**, matching the order the panels render in. The selection's
 * own order is not preserved anywhere: `_select_concepts` orders by catalogue
 * and `selectMetricIds` does the same, so a reversed request comes back in
 * catalogue order (verified in the growth report). Presenting the options in
 * any other order would imply a control the builders do not offer.
 */
import type { ChartId, Metric } from "./contracts.ts";
import { defaultSelection } from "./charts/defaults.ts";

export default function MetricPicker({
  chart,
  offerable,
  selected,
  byId,
  onChange,
}: {
  chart: ChartId;
  /** The narrowed catalogue, in catalogue order. */
  offerable: readonly string[];
  selected: readonly string[];
  byId: Map<string, Metric>;
  onChange: (next: string[]) => void;
}) {
  const chosen = new Set(selected);
  // Always rebuilt by filtering `offerable`, never by pushing onto `selected`:
  // that keeps catalogue order regardless of the order boxes are ticked.
  const setTo = (ids: Set<string>) => onChange(offerable.filter((id) => ids.has(id)));
  const toggle = (id: string) => {
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setTo(next);
  };

  const isDefault =
    selected.length === 1 && selected[0] === defaultSelection(chart, offerable)[0];

  return (
    <fieldset style={{ border: "1px solid #ccc", borderRadius: 4, padding: "0.5rem 0.75rem" }}>
      <legend>
        Metrics — {selected.length} of {offerable.length} offered for this profile{" "}
        <button type="button" onClick={() => setTo(new Set(offerable))}
                disabled={selected.length === offerable.length}>
          All
        </button>{" "}
        {/* Clearing is a real state, not a mistake: the empty selection is what
            `concepts=[]` means to every builder, and migrateSelection honours
            it across a ticker switch rather than filling it back in. */}
        <button type="button" onClick={() => onChange([])} disabled={selected.length === 0}>
          None
        </button>{" "}
        <button type="button" onClick={() => onChange(defaultSelection(chart, offerable))}
                disabled={isDefault}>
          Default
        </button>
      </legend>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.15rem 1rem" }}>
        {offerable.map((id) => {
          const metric = byId.get(id);
          return (
            <label key={id} style={{ whiteSpace: "nowrap" }}>
              <input type="checkbox" checked={chosen.has(id)} onChange={() => toggle(id)} />{" "}
              {metric ? metric.label : id}{" "}
              <code style={{ opacity: 0.55, fontSize: "0.85em" }}>{id}</code>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
