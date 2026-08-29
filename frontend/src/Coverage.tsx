/**
 * Profile coverage — `render_coverage` (app.py:676), the second and last
 * reference view.
 *
 * **Two views of one thing, and the reference says why in its own caption**
 * (app.py:707): *"The per-profile view above answers 'what does this company
 * show'; this answers 'who sees this metric', which is the question the matrix
 * is uniquely good at."* So this is not "a 24 × 52 matrix" with a preamble —
 * it is a selector-driven per-profile reading, then the transpose, and both are
 * load-bearing.
 *
 * **This page reads `profile_visibility`; it never re-derives it.** Every chart,
 * picker and builder since item 4 has depended on `is_hidden`, and item 1
 * verified the export against `get_plottable_metrics` over all 1,827
 * (profile, metric) pairs. Adding a client-side `isHidden` here would create a
 * second answer to a question that already has one — exactly the failure items
 * 17 and 18 were built to make structurally impossible. Every ✓ and every `·`
 * below is `registry.profile_visibility[profile][id]`, read and not computed.
 *
 * **No tabs, unlike item 20.** `render_coverage` runs its three `CHART_SECTIONS`
 * as consecutive `st.subheader`s (app.py:694-703), not `st.tabs` — the point is
 * to read a profile's whole shape in one pass, and hiding two thirds of it
 * behind tabs would defeat that. Same section list, same order; different
 * container, because the reference's is different.
 */
import { useMemo, useState } from "react";
import type { ChartId, Metric, Registry } from "./contracts.ts";
import "./coverage.css";

/** `CHART_SECTIONS` (app.py:86) again — the ids and titles only; the blurbs belong to the encyclopedia. */
const SECTIONS: readonly { chart: ChartId; title: string }[] = [
  { chart: "fundamentals", title: "Fundamentals" },
  { chart: "valuation", title: "Valuation" },
  { chart: "growth", title: "Growth" },
];

/** A comma-separated run of backticked labels — `st.markdown`'s ", ".join(f"`{…}`"). */
function LabelList({ lead, labels }: { lead: string; labels: readonly string[] }) {
  return (
    <p className="coverage__list">
      <strong>{lead}</strong>{" "}
      {labels.map((label, i) => (
        <span key={label}>
          {i > 0 && ", "}
          <code>{label}</code>
        </span>
      ))}
    </p>
  );
}

export default function Coverage({ registry }: { registry: Registry }) {
  // app.py:685-686 `sorted(visibility)` -- ascending by code point, which for
  // these lowercase ASCII names is Python's own order.
  const profiles = useMemo(
    () => Object.keys(registry.profile_visibility).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0)),
    [registry],
  );
  // app.py:689-690 -- `standard` when it exists, else the first. Not
  // `registry.default_profile`: the reference names the string literally here,
  // and the two agreeing today is not the same as them being one thing.
  const [profile, setProfile] = useState(
    () => (profiles.includes("standard") ? "standard" : profiles[0]) ?? "",
  );

  const byId = useMemo(
    () => new Map(registry.metrics.map((m) => [m.id, m] as const)),
    [registry],
  );
  // Its own memo, not an inline `?? {}`: a fresh empty object every render would
  // make both memos below re-run every render, which eslint is right to flag.
  const visible = useMemo(
    () => registry.profile_visibility[profile] ?? {},
    [registry, profile],
  );

  // app.py:691 `sum(visibility[profile].values())` -- across every registered
  // metric, not per chart. The denominator is `len(by_id)` (app.py:692): all 52,
  // which is also what makes the three per-section counts below add up to it.
  const shownTotal = useMemo(
    () => registry.metrics.reduce((n, m) => n + (visible[m.id] ? 1 : 0), 0),
    [registry, visible],
  );

  const sections = useMemo(
    () =>
      SECTIONS.map(({ chart, title }) => {
        const ids = registry.metrics.filter((m) => m.chart === chart).map((m) => m.id);
        return {
          title,
          total: ids.length,
          shown: ids.filter((id) => visible[id]),
          hidden: ids.filter((id) => !visible[id]),
        };
      }),
    [registry, visible],
  );

  const label = (id: string) => (byId.get(id) as Metric).label;

  return (
    <section className="coverage">
      <h2>Profile coverage</h2>
      {/* app.py:678-683, verbatim -- including the trailing space the reference
          leaves inside the string, which renders as nothing. */}
      <p className="coverage__lede">
        Which metrics each business profile shows, and which it suppresses. A bank has no inventory
        and a REIT is not valued on earnings, so showing every metric for every company would mean
        showing numbers that do not mean anything.
      </p>

      {/* app.py:688 `st.selectbox("Profile", profiles, ...)`. */}
      <label className="coverage__picker">
        Profile
        <select value={profile} onChange={(e) => setProfile(e.target.value)}>
          {profiles.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </label>

      <p className="caption">
        <code>{profile}</code> shows {shownTotal} of {registry.metrics.length} registered metrics.
      </p>

      {sections.map(({ title, total, shown, hidden }) => (
        <section key={title} className="coverage__section">
          {/* app.py:698 -- the section's own count, `{shown} of {ids}`, which is
              the chart's total and not the registry's. */}
          <h3>
            {title} — {shown.length} of {total}
          </h3>
          {/* Each list is rendered only when it has entries (app.py:699/701), so
              a profile that hides nothing in a section shows one line, not an
              empty "Hidden" heading. */}
          {shown.length > 0 && <LabelList lead="Shown:" labels={shown.map(label)} />}
          {hidden.length > 0 && (
            <LabelList lead="Hidden for this profile:" labels={hidden.map(label)} />
          )}
        </section>
      ))}

      <hr />

      <h3>Full matrix</h3>
      {/* app.py:706-710, verbatim. "Scrolls horizontally" is a promise about the
          widget, and `.table-scroll` is what keeps it true here. */}
      <p className="caption">
        {registry.metrics.length} metrics × {profiles.length} profiles. The per-profile view above
        answers &quot;what does this company show&quot;; this answers &quot;who sees this
        metric&quot;, which is the question the matrix is uniquely good at. Scrolls horizontally.
      </p>

      {/*
       * `.table-scroll` + `.data-table` are the data tab's, reused rather than
       * restated: this is the same object -- a wide table with a pinned first
       * column and a sticky header -- and the corner rule is exactly what stops
       * a reader losing which metric a column of ticks belongs to. It is outside
       * `.data-tab`, so `check-table-format`'s scan cannot see it.
       */}
      <div className="table-scroll">
        <table className="data-table coverage__matrix">
          <caption className="sr-only">Metric visibility by business profile</caption>
          <thead>
            <tr>
              <th scope="col" className="data-table__corner">
                metric
              </th>
              <th scope="col">chart</th>
              <th scope="col">profiles</th>
              {profiles.map((p) => (
                <th scope="col" key={p}>
                  {p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* app.py:711 iterates `config.METRICS` -- registry order, the same
                order the encyclopedia and every chart's panels use. */}
            {registry.metrics.map((metric) => {
              const seenBy = profiles.reduce(
                (n, p) => n + (registry.profile_visibility[p][metric.id] ? 1 : 0),
                0,
              );
              return (
                <tr key={metric.id}>
                  <th scope="row" className="data-table__corner">
                    {metric.label}
                  </th>
                  <td className="cell coverage__chart">{metric.chart}</td>
                  <td className="cell">{seenBy}</td>
                  {profiles.map((p) => {
                    const on = registry.profile_visibility[p][metric.id];
                    return (
                      <td
                        key={p}
                        className={on ? "cell coverage__on" : "cell coverage__off"}
                        title={`${metric.label} — ${p}: ${on ? "shown" : "hidden"}`}
                      >
                        {/* app.py:714 -- a tick or a middle dot, not a checkbox
                            and not a blank: an unmarked cell would read as "no
                            answer" where the answer is "hidden". */}
                        {on ? "✓" : "·"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
