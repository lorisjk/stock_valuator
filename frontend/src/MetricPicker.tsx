/**
 * The metric picker: one checkbox per id the ticker's profile offers.
 *
 * The options are the narrowed catalogue and nothing else.
 * `offerable` comes from `selectMetricIds(...)`, so a metric hidden by
 * `profile_visibility` is never rendered as an option.
 *
 * The picker uses a searchable multi-select combobox. Both the readable
 * metric label and the underlying metric id can be searched.
 *
 * Catalogue order is preserved: selections are always rebuilt by filtering
 * `offerable`, never by appending to the current selection.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { ChartId, Metric } from "./contracts.ts";
import { defaultSelection } from "./charts/defaults.ts";
import "./metric-picker.css";

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
  /*
   * --------------------------------------------------------------------------
   * SELECTION
   * --------------------------------------------------------------------------
   */

  const chosen = useMemo(
    () => new Set(selected),
    [selected],
  );

  /*
   * Always rebuild the selection by filtering `offerable`.
   *
   * This keeps catalogue order regardless of the order in which the user
   * clicks the checkboxes.
   */
  const setTo = (ids: Set<string>) => {
    onChange(
      offerable.filter((id) => ids.has(id)),
    );
  };

  const toggle = (id: string) => {
    const next = new Set(chosen);

    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }

    setTo(next);
  };

  /*
   * --------------------------------------------------------------------------
   * COMBOBOX STATE
   * --------------------------------------------------------------------------
   */

  const [comboOpen, setComboOpen] = useState(false);

  const [metricSearch, setMetricSearch] = useState("");

  const comboRef = useRef<HTMLDivElement>(null);

  /*
   * --------------------------------------------------------------------------
   * SEARCH RESULTS
   * --------------------------------------------------------------------------
   *
   * Search both:
   *
   *   - metric label
   *   - metric id
   *
   * Example:
   *
   *   "shares" -> Shares Outstanding
   *   "pe"     -> P/E (TTM)
   *   "pe_ratio" -> pe_ratio
   */

  const filteredOfferable = useMemo(() => {
    const query = metricSearch.trim().toLowerCase();

    if (!query) {
      return offerable;
    }

    return offerable.filter((id) => {
      const metric = byId.get(id);

      const label = metric?.label ?? "";

      return (
        id.toLowerCase().includes(query) ||
        label.toLowerCase().includes(query)
      );
    });
  }, [offerable, byId, metricSearch]);

  /*
   * --------------------------------------------------------------------------
   * DEFAULT STATE
   * --------------------------------------------------------------------------
   */

  const isDefault =
    selected.length === 1 &&
    selected[0] === defaultSelection(chart, offerable)[0];

  /*
   * --------------------------------------------------------------------------
   * CLOSE ON OUTSIDE CLICK
   * --------------------------------------------------------------------------
   */

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        comboRef.current &&
        event.target instanceof Node &&
        !comboRef.current.contains(event.target)
      ) {
        setComboOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleClickOutside,
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside,
      );
    };
  }, []);

  /*
   * --------------------------------------------------------------------------
   * RENDER
   * --------------------------------------------------------------------------
   */

  return (
    <fieldset className="metric-picker">

      <legend>
        Metrics — {selected.length} of {offerable.length} offered for this profile{" "}

        <button
          type="button"
          onClick={() => setTo(new Set(offerable))}
          disabled={selected.length === offerable.length}
        >
          All
        </button>{" "}

        <button
          type="button"
          onClick={() => onChange([])}
          disabled={selected.length === 0}
        >
          None
        </button>{" "}

        <button
          type="button"
          onClick={() =>
            onChange(
              defaultSelection(chart, offerable),
            )
          }
          disabled={isDefault}
        >
          Default
        </button>
      </legend>

      {/* ------------------------------------------------------------------ */}
      {/* COMBOBOX                                                          */}
      {/* ------------------------------------------------------------------ */}

      <div
        ref={comboRef}
        className="metric-picker__combobox"
      >

        {/* -------------------------------------------------------------- */}
        {/* TRIGGER                                                        */}
        {/* -------------------------------------------------------------- */}

        <button
          type="button"
          className="metric-picker__combobox-trigger"
          onClick={() => {
            setComboOpen((open) => !open);

            /*
             * Start with an empty search whenever the menu is opened.
             */
            if (!comboOpen) {
              setMetricSearch("");
            }
          }}
          aria-expanded={comboOpen}
          aria-haspopup="listbox"
        >
          <span>
            {selected.length === 0
              ? "Select metrics..."
              : `${selected.length} metric${
                  selected.length === 1 ? "" : "s"
                } selected`}
          </span>

          <span className="metric-picker__combobox-arrow">
            {comboOpen ? "▲" : "▼"}
          </span>
        </button>

        {/* -------------------------------------------------------------- */}
        {/* DROPDOWN                                                       */}
        {/* -------------------------------------------------------------- */}

        {comboOpen && (
          <div className="metric-picker__combobox-menu">

            {/* Search field */}
            <div className="metric-picker__search">
              <input
                type="text"
                value={metricSearch}
                onChange={(e) =>
                  setMetricSearch(e.target.value)
                }
                placeholder="Search metrics..."
                autoFocus
              />
            </div>

            {/* Results */}
            <div className="metric-picker__options">

              {filteredOfferable.length === 0 ? (
                <div className="metric-picker__empty">
                  No metrics found.
                </div>
              ) : (
                filteredOfferable.map((id) => {
                  const metric = byId.get(id);

                  return (
                    <label
                      key={id}
                      className="metric-picker__option"
                    >
                      <input
                        type="checkbox"
                        checked={chosen.has(id)}
                        onChange={() => toggle(id)}
                      />

                      <span className="metric-picker__option-content">
                        <span className="metric-picker__option-label">
                          {metric ? metric.label : id}
                        </span>

                        <code className="metric-picker__option-id">
                          {id}
                        </code>
                      </span>
                    </label>
                  );
                })
              )}

            </div>
          </div>
        )}
      </div>
    </fieldset>
  );
}