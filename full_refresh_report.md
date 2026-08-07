# Full Refresh Report

## Run metadata

- Start: 2026-08-06T19:21:29
- End: 2026-08-06T19:22:22
- Total wall-clock time: 52.8s (0.9 min)
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
- Total: 23.2s across 8 tickers
- Average per ticker: 2.90s
- Slowest 10 tickers:
  - O: 5.46s
  - JPM: 3.21s
  - BAC: 2.97s
  - AMT: 2.47s
  - AFL: 2.42s
  - AZO: 2.36s
  - MSFT: 2.32s
  - AAPL: 2.01s

### Phase 2 -- yfinance fetch
- Total: 7.7s across 8 tickers
- Average per ticker: 0.96s
- Slowest 10 tickers:
  - AAPL: 1.86s
  - O: 1.19s
  - JPM: 1.03s
  - BAC: 0.88s
  - AFL: 0.79s
  - AMT: 0.68s
  - MSFT: 0.65s
  - AZO: 0.60s

### Phase 3 -- Calculate + plot
- Calculate (calculate_all_metrics/build_metrics_long/build_valuation_history/build_snapshot, whole batch, one run -- not decomposed per ticker, since doing so would mean calling these functions once per ticker instead of once for the batch, a change to how the calculation runs rather than pure instrumentation): 11.4s
- Plot (per ticker, all three charts): total 7.9s across 8 tickers, average 0.99s/ticker
- Slowest 10 tickers (plotting):
  - AAPL: 1.89s
  - AZO: 1.06s
  - MSFT: 1.04s
  - AFL: 0.85s
  - BAC: 0.80s
  - JPM: 0.80s
  - O: 0.74s
  - AMT: 0.72s

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
- **thin** O `StockRepurchased`: 4 of 70 (6%) -- `python explore_tags.py O repurchase treasurystock buyback`
- **thin** O `PretaxIncome`: 24 of 70 (34%)

### retail

- **MISSING** AZO `DividendsPerShare`: 0 of 73 (0%) -- `python explore_tags.py AZO dividendspershare`
- **MISSING** AZO `StockIssued`: 0 of 73 (0%) -- `python explore_tags.py AZO issuanceofcommon stockissuedduringperiodvalue saleofequity`

### standard

- **thin** AAPL `Goodwill`: 36 of 75 (48%) -- `python explore_tags.py AAPL goodwill intangible`
