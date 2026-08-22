/**
 * The subplot grid, and the axis/domain arithmetic plotly.py's make_subplots
 * does for the Python builder.
 *
 * This is the piece that forces a rebuild rather than a client-side toggle:
 * rows and columns are derived from the panel count, and a finished figure
 * cannot be re-tiled. Deselecting a metric is therefore a rebuild, not a
 * visibility change (inventory 4.1).
 */

export const MAX_COLS = 3;

/** figures.py `_make_grid`: cols = min(3, n), rows = ceil(n / cols). */
export function makeGrid(n: number, maxCols = MAX_COLS): { rows: number; cols: number } {
  if (n === 0) return { rows: 1, cols: 1 };
  const cols = Math.min(maxCols, n);
  return { rows: Math.ceil(n / cols), cols };
}

/**
 * 1-based (row, col) for the idx-th panel, filling left to right, top to bottom
 * -- the order build_valuation walks its concept list in.
 */
export const cellFor = (idx: number, cols: number) => ({
  row: Math.floor(idx / cols) + 1,
  col: (idx % cols) + 1,
});

/** plotly's axis suffix: 1 -> "", 2 -> "2", ... */
export const axisSuffix = (n: number) => (n === 1 ? "" : String(n));

/** 1-based axis number for a cell, matching make_subplots' numbering. */
export const axisNumber = (row: number, col: number, cols: number) => (row - 1) * cols + col;

export interface Domain {
  x: [number, number];
  y: [number, number];
}

/**
 * The x/y domain of one cell, matching make_subplots' defaults.
 *
 * Horizontal spacing is 0.2/cols. Vertical is **0.5/rows, not 0.3/rows**: 0.3
 * is plotly.py's default only when no subplot titles are given, and it widens
 * the gap to 0.5 to make room for them. Every grid here has titles. Getting
 * this wrong is silent -- the panels still tile, they just overlap their own
 * titles -- which is why the domains are compared against the reference figure
 * rather than eyeballed.
 */
export function cellDomain(row: number, col: number, rows: number, cols: number): Domain {
  const hSpace = 0.2 / cols;
  const vSpace = 0.5 / rows;
  const width = (1 - hSpace * (cols - 1)) / cols;
  const height = (1 - vSpace * (rows - 1)) / rows;
  const x0 = (col - 1) * (width + hSpace);
  // Domains are measured from the bottom of the paper; row 1 sits at the top.
  const y1 = 1 - (row - 1) * (height + vSpace);
  return { x: [round(x0), round(x0 + width)], y: [round(y1 - height), round(y1)] };
}

const round = (v: number) => Math.round(v * 1e9) / 1e9;
