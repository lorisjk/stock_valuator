# stock_valuator

A fundamental analysis tool for publicly traded US companies. Pulls financials from SEC EDGAR, prices from yfinance, computes fifteen metrics, and writes two chart sets per ticker.

The question it answers is not "what is this company worth" but **"is this stock expensive relative to its own history, and is the business behind it healthy"**.

---

## Why not just use yfinance's numbers

`yf.Ticker(x).info` already returns `trailingPE`, `priceToBook`, `enterpriseToEbitda` and most of the rest. They are not used here.

The methodology behind those figures is undocumented — which EPS definition, which period, what happens when a tag is missing. Everything in this project is computed from raw SEC filings, so every number can be traced back to a specific 10-Q or 10-K. yfinance supplies prices only.

---

## Setup

```bash
pip install -r requirements.txt
```

Set your contact details in `config.py` — the SEC rejects requests without a real name and email in the User-Agent:

```python
EDGAR_USER_AGENT = "Your Name your@email.com"
TICKERS = ["AAPL", "MSFT", "NVDA"]
```

```bash
python main.py
```

---

## Output

**`data/`**
| File | Contents |
|---|---|
| `quarterly_facts.csv` | Raw concepts per ticker and quarter |
| `metrics_long.csv` | Nine fundamental metrics, full history |
| `valuation_history.csv` | Six valuation multiples, full history |
| `current_snapshot.csv` | One row per ticker, all current figures |

**`figures/`**
| File | Contents |
|---|---|
| `<TICKER>_fundamentals.png` | 3×3 grid: growth, margins, returns, leverage — full history |
| `<TICKER>_valuation.png` | 2×3 grid: P/E, P/B, P/FCF, EV/EBITDA, EV/Sales, dividend yield — last 5 years, each with its own mean |

Charts are always per ticker, never across tickers. A P/E of 30 means little next to a competitor's 25; it means something next to that company's own five-year average.

---

## Metrics

**Fundamentals** (business health, full history, TTM-smoothed)
Revenue growth · earnings growth · operating margin · FCF margin · ROE · debt/equity · net debt/EBITDA · payout ratio · Rule of 40

**Valuation** (price-based, last 5 years)
P/E (TTM) · P/B · P/FCF · EV/EBITDA · EV/Sales · dividend yield · PEG · 5-year average P/E

---

## Structure

```
main.py          Pipeline orchestration
config.py        Tickers, XBRL tag mapping, paths
metrics.py       Generic DataFrame calculations
figures.py       Plotting
quality.py       Data coverage check
fetchers/
  edgar.py       SEC EDGAR: fetch, cache, extract
  yfinance_fetcher.py
parsers/
  parse_edgar.py Tag resolution, facts table assembly
```

Each module has a `_doc.md` with details on the design decisions and the data problems it solves.

---

## Notes on the data

SEC filings are messier than they look. Handled by this tool:

- **The `fp` field lies.** Some companies tag every value as `FY`, including quarters. Period classification uses the actual date span instead.
- **Cash flow items are cumulative.** Operating cash flow, capex and D&A are reported year-to-date, not per quarter. They are decumulated automatically.
- **Q4 is never filed.** It is derived as `FY − (Q1+Q2+Q3)`.
- **Tags change and differ.** Revenue moved tags in 2018; Microsoft splits D&A into two positions; Walmart reports EPS under two units. Handled via configurable fallback and summation strategies.
- **Splits corrupt per-share values.** EDGAR restates EPS retroactively but inconsistently. TTM EPS is therefore computed from absolute figures (`net income / share count`), never by summing quarterly EPS.

Adding a new ticker runs a coverage check that reports any concept that is missing or thin.

---

## Limitations

**No forward-looking metrics.** Forward P/E needs analyst estimates; EDGAR has none.

**No non-GAAP figures.** Companies define their own adjustments, and they only appear in 8-K press releases, not in structured XBRL.

**Not suitable for financial companies.** Banks have no operating income, no meaningful capex, and no long-term debt in the sense these metrics assume — debt is their raw material. Around half the charts come out empty for JPM, which is the correct answer, not a bug. Financials need a different metric set entirely.
