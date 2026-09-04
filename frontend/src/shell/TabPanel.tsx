/**
 * One Analysis tab's slot: mounted on first visit, kept mounted afterwards.
 *
 * **Why this exists as a component rather than three lines in `App.tsx`.** The
 * shell had two mounting rules and no way to tell they were two: `ChartView` was
 * mounted up front and hidden with `hidden`, so its picker and window survived a
 * tab switch, while `ComparisonView` was rendered as `{tab === "comparison" &&
 * <ComparisonView/>}` and was therefore *unmounted* on the way out. React
 * discards a component's `useState` when it unmounts and re-runs the
 * initialisers on the way back, so the comparison tab silently reset its ticker
 * set, its metric and its window every time the reader glanced at another tab.
 * The state was never lifted anywhere; there was nothing to read back.
 *
 * Both tabs already stored their state the same way -- plain `useState` inside
 * the view. The *only* difference was mount lifetime, which is why the fix is
 * this and not a store: one rule, applied once, for every tab.
 *
 * **`hidden`, not a CSS class**, for the same reason `ChartView` used it: it is
 * the platform's own "this subtree is not currently relevant", so it takes the
 * accessibility tree and find-in-page with it, and no stylesheet has to agree.
 *
 * **Mounted lazily, not up front**, because the two heaviest tabs each fetch on
 * mount -- `DataTab` pulls `facts_full`, the largest file in the export, and
 * `ComparisonView` pulls one core file per ticker in its set. Mounting all six
 * tabs on load would fetch both for someone who only opened a chart. The latch
 * is the whole cost of having it both ways, and it is one boolean.
 *
 * The latch is adjusted **during render**, which is React's documented pattern
 * for state derived from a prop rather than a wart: it is what mounts the tab in
 * the render that first needs it instead of one render later, and one render
 * later is exactly when a `<Plot>` inside would measure a hidden container. The
 * `!seen` guard is what makes it run once.
 */
import { useState, type ReactNode } from "react";
import type { TabId } from "./navigation.ts";

export default function TabPanel({
  id,
  active,
  children,
}: {
  /** The tab this slot is for. */
  id: TabId;
  /** The tab currently selected. */
  active: TabId;
  /**
   * Built by the caller on every render, but only *mounted* once this slot has
   * been visited -- an unrendered element is a plain object and costs nothing.
   */
  children: ReactNode;
}) {
  const [seen, setSeen] = useState(active === id);
  if (!seen && active === id) setSeen(true);
  if (!seen) return null;
  return <div hidden={active !== id}>{children}</div>;
}
