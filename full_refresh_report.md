# Full Refresh Report

## Run metadata

- Start: 2026-08-06T10:19:44
- End: 2026-08-06T10:20:30
- Total wall-clock time: 46.2s (0.8 min)
- Active tickers processed: 8
- Cached facts files deleted: 24

<details><summary>Deleted cache files</summary>

- `cache\AAPL_company_info.json`
- `cache\AAPL_submissions.json`
- `cache\AAPL_cache_meta.json`
- `cache\AFL_company_info.json`
- `cache\AFL_submissions.json`
- `cache\AFL_cache_meta.json`
- `cache\AMT_company_info.json`
- `cache\AMT_submissions.json`
- `cache\AMT_cache_meta.json`
- `cache\AZO_company_info.json`
- `cache\AZO_submissions.json`
- `cache\AZO_cache_meta.json`
- `cache\BAC_company_info.json`
- `cache\BAC_submissions.json`
- `cache\BAC_cache_meta.json`
- `cache\JPM_company_info.json`
- `cache\JPM_submissions.json`
- `cache\JPM_cache_meta.json`
- `cache\MSFT_company_info.json`
- `cache\MSFT_submissions.json`
- `cache\MSFT_cache_meta.json`
- `cache\O_company_info.json`
- `cache\O_submissions.json`
- `cache\O_cache_meta.json`

</details>

## Timing

### Phase 1 -- EDGAR fetch
- Total: 19.8s across 8 tickers
- Average per ticker: 2.48s
- Slowest 10 tickers:
  - JPM: 3.40s
  - BAC: 2.90s
  - AFL: 2.68s
  - AMT: 2.35s
  - AZO: 2.29s
  - MSFT: 2.26s
  - AAPL: 2.08s
  - O: 1.89s

### Phase 2 -- yfinance fetch
- Total: 7.4s across 8 tickers
- Average per ticker: 0.92s
- Slowest 10 tickers:
  - AAPL: 1.62s
  - AMT: 1.01s
  - AFL: 0.90s
  - O: 0.87s
  - BAC: 0.80s
  - JPM: 0.75s
  - AZO: 0.73s
  - MSFT: 0.72s

### Phase 3 -- Calculate + plot
- Calculate (calculate_all_metrics/build_metrics_long/build_valuation_history/build_snapshot, whole batch, one run -- not decomposed per ticker, since doing so would mean calling these functions once per ticker instead of once for the batch, a change to how the calculation runs rather than pure instrumentation): 10.5s
- Plot (per ticker, all three charts): total 6.3s across 8 tickers, average 0.79s/ticker
- Slowest 10 tickers (plotting):
  - AAPL: 1.60s
  - MSFT: 0.86s
  - AZO: 0.82s
  - BAC: 0.66s
  - AFL: 0.65s
  - JPM: 0.64s
  - O: 0.57s
  - AMT: 0.54s

## Data quality flags

12 flags across 5 profiles.

### financial

- **thin** BAC `StockIssued`: 32 of 75 (43%) -- `python explore_tags.py BAC issuanceofcommon stockissuedduringperiodvalue saleofequity`
- **thin** JPM `StockIssued`: 2 of 73 (3%) -- `python explore_tags.py JPM issuanceofcommon stockissuedduringperiodvalue saleofequity`

### insurance_life

- **MISSING** AFL `Investments`: 0 of 73 (0%) -- `python explore_tags.py AFL investments`
- **MISSING** AFL `ShareBasedCompensation`: 0 of 73 (0%)
- **MISSING** AFL `StockIssued`: 0 of 73 (0%) -- `python explore_tags.py AFL issuanceofcommon stockissuedduringperiodvalue saleofequity`
- **thin** AFL `Goodwill`: 7 of 73 (10%) -- `python explore_tags.py AFL goodwill intangible`

### reit

- **MISSING** AMT `GainLossOnSaleOfProperties`: 0 of 74 (0%)
- **thin** O `StockRepurchased`: 2 of 69 (3%) -- `python explore_tags.py O repurchase treasurystock buyback`
- **thin** O `PretaxIncome`: 23 of 69 (33%)

### retail

- **MISSING** AZO `DividendsPerShare`: 0 of 73 (0%) -- `python explore_tags.py AZO dividendspershare`
- **MISSING** AZO `StockIssued`: 0 of 73 (0%) -- `python explore_tags.py AZO issuanceofcommon stockissuedduringperiodvalue saleofequity`

### standard

- **thin** AAPL `Goodwill`: 36 of 75 (48%) -- `python explore_tags.py AAPL goodwill intangible`
