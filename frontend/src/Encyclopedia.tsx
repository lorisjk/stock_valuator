/**
 * The Metric encyclopedia — `render_encyclopedia` (app.py:632), the first of the
 * two ticker-independent reference views.
 *
 * **Almost no computation, and that is the shape of the work.** Every field this
 * page renders — `label`, `description`, `formula`, `chart`, `documented` — is
 * already in `registry.json`, already loaded by `DataProvider` for the pickers,
 * and already verified equivalent to `config.METRICS`. Nothing here derives
 * anything; the decisions are grouping, ordering, and what an *undocumented*
 * metric looks like.
 *
 * **Registry order, not alphabetical.** `entries = [m for m in config.METRICS if
 * m.chart == chart]` (app.py:657) preserves the registry's own sequence, which
 * is the same order every chart's panels have been drawn in since item 4. A
 * reader who has the Fundamentals chart open sees its panels and this page's
 * entries in the same sequence, and that is worth more than alphabetisation.
 *
 * **The tab order is not the Analysis tabs' order.** `CHART_SECTIONS`
 * (app.py:86) is Fundamentals, Valuation, Growth; the Analysis tabs are Growth,
 * Fundamentals, Valuation. Two different lists in the reference, and the
 * difference is carried rather than smoothed: this page reads "what the business
 * does → what the market charges for it → how it changed", which is an argument,
 * not a sort.
 *
 * **The tab strip reuses `.tabs`/`.tab`.** Streamlit draws `st.tabs` the same
 * way in both places, and a view switch unmounts the Analysis shell entirely, so
 * the two strips can never be on screen at once.
 */
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { ChartId, Metric, Registry } from "./contracts.ts";
import "./encyclopedia.css";

/**
 * `CHART_SECTIONS` (app.py:86-91), verbatim: the id, the tab title and the
 * one-line blurb `st.caption`'d under it.
 *
 * Note `"Growth"` here against `CHART_LABELS`' `"Growth (YoY)"` in the Analysis
 * tabs — the reference keeps two spellings and this is the one that renders on
 * this page.
 */
const SECTIONS: readonly { chart: ChartId; title: string; blurb: string }[] = [
  {
    chart: "fundamentals",
    title: "Fundamentals",
    blurb: "What the business does, independent of its share price.",
  },
  {
    chart: "valuation",
    title: "Valuation",
    blurb: "What the market charges for a claim on that business.",
  },
  {
    chart: "growth",
    title: "Growth",
    blurb: "Year-over-year change in the underlying filed figures.",
  },
];

/**
 * app.py:658-662. The query is already `.strip().lower()`'d by the caller; a
 * metric matches if it appears in any of the four fields, and a missing
 * description or formula is treated as `""` rather than skipped — `(m.description
 * or "")` — so an undocumented metric can still be found by its id or label.
 */
function matches(metric: Metric, query: string): boolean {
  return (
    metric.id.toLowerCase().includes(query) ||
    metric.label.toLowerCase().includes(query) ||
    (metric.description ?? "").toLowerCase().includes(query) ||
    (metric.formula ?? "").toLowerCase().includes(query)
  );
}

/**
 * One metric: `#### {label}`, the id as a caption, then either its documentation
 * or the honest gap (app.py:666-673).
 *
 * The description and the formula line both go through markdown because they are
 * written as markdown — 50 of the 52 registry entries carry backticked concept
 * names, and `st.markdown` is what renders them in the reference. The
 * `**How it is computed:**` prefix is part of that same string, not a label
 * wrapped around it.
 */
function Entry({ metric }: { metric: Metric }) {
  return (
   
    <article className="entry">
      <h4>{metric.label}</h4>
      <p className="caption">
        <code>{metric.id}</code>
      </p>
      {metric.documented ? (
        <>
          <div className="entry__prose">
            <ReactMarkdown>{metric.description ?? ""}</ReactMarkdown>
          </div>
          <div className="entry__prose">
            <ReactMarkdown>{`**How it is computed:** ${metric.formula ?? ""}`}</ReactMarkdown>
          </div>
        </>
      ) : (
        /* app.py:673. The entry is **shown**, with its label and id, and says
           plainly that the text is missing -- it is neither omitted nor filled
           with something plausible. Unreachable on today's registry (all 52 are
           documented) and implemented anyway, because the branch is what makes a
           future undocumented metric visible rather than blank. */
        <p className="notice-inline">Not documented yet — see the report&apos;s gap list.</p>
      )}
      <hr />
    </article>
  );
}

export default function Encyclopedia({ registry }: { registry: Registry }) {
  const [rawQuery, setRawQuery] = useState("");
  const [section, setSection] = useState<ChartId>(SECTIONS[0].chart);
  // app.py:643 `.strip().lower()` -- done once, so every comparison below is
  // against the same normalised string the reference compares against.
  const query = rawQuery.trim().toLowerCase();

  const shown = useMemo(() => {
    const spec = SECTIONS.find((s) => s.chart === section) ?? SECTIONS[0];
    const entries = registry.metrics.filter((m) => m.chart === spec.chart);
    return { spec, entries: query === "" ? entries : entries.filter((m) => matches(m, query)) };
  }, [registry, section, query]);

  // app.py:640 `config.undocumented_metrics()`, exported as `registry.undocumented`.
  const undocumented = registry.undocumented;

  return (
    <section className="encyclopedia">
      <hr />
      <h2>Metric encyclopedia</h2>
      {/* app.py:634-638, verbatim. */}
      <p className="encyclopedia__lede">
        Every metric this pipeline computes, with the formula it actually uses. These are read off
        the implementation, not from a textbook — where the two differ, what is written here is what
        the code does.
      </p>

      {/* app.py:641 `st.warning`. `.notice-inline` is this build's established
          rendering for one -- `ComparisonView` already uses it for the
          exclusion warnings -- so the two agree rather than each inventing a
          callout. Empty today; the list is the page's own gap report. */}
      {undocumented.length > 0 && (
        <p className="notice-inline encyclopedia__undocumented" role="status">
          Undocumented metrics:{" "}
          {undocumented.map((id, i) => (
            <span key={id}>
              {i > 0 && ", "}
              <code>{id}</code>
            </span>
          ))}
        </p>
      )}

      {/* app.py:643 `st.text_input("Filter", placeholder=...)`. */}
      <label className="encyclopedia__filter">
        Filter
        <input
          type="search"
          value={rawQuery}
          placeholder="e.g. margin, EBITDA, p_tbv"
          onChange={(e) => setRawQuery(e.target.value)}
        />
      </label>

      <nav className="tabs" aria-label="Metric groups">
        {SECTIONS.map(({ chart, title }) => (
          <button
            key={chart}
            type="button"
            className={chart === section ? "tab tab--active" : "tab"}
            aria-current={chart === section ? "page" : undefined}
            onClick={() => setSection(chart)}
          >
            {title}
          </button>
        ))}
      </nav>

      <p className="caption">{shown.spec.blurb}</p>

      {/* app.py:649-654 -- the mechanism notes belong to two of the three groups
          and render *before* the entries, each followed by a divider.
          Fundamentals has none, which is not an omission: the note explains a
          shared mechanism, and the fundamentals metrics share no single one.

          They live here rather than on the charts they describe because that is
          where the reference puts them, and because they are reference material
          about how a whole family of panels is produced -- the same reason this
          page exists. */}
      {shown.spec.chart === "growth" && (
        <div className="mechanism">
          <ReactMarkdown>{registry.notes.growth_mechanism}</ReactMarkdown>
          <hr />
        </div>
      )}
      {shown.spec.chart === "valuation" && (
        <div className="mechanism">
          <ReactMarkdown>{registry.notes.valuation_mechanism}</ReactMarkdown>
          <hr />
        </div>
      )}

      {shown.entries.length === 0 ? (
        /* app.py:664. Per section, so a query can empty one group and leave the
           next one full -- the reference filters inside each tab. */
        <p className="notice-inline encyclopedia__empty" role="status">
          Nothing matches that filter in this section.
        </p>
      ) : (
        shown.entries.map((metric) => <Entry key={metric.id} metric={metric} />)
      )}
    </section>
  );
}
