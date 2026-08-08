# Full Refresh Report

## Run metadata

- Start: 2026-08-08T22:32:00
- End: 2026-08-08T22:32:43
- Total wall-clock time: 42.6s (0.7 min)
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

### Phase 1 -- yfinance fetch
- Total: 6.7s across 8 tickers
- Average per ticker: 0.84s
- Slowest 10 tickers:
  - AAPL: 1.48s
  - O: 1.04s
  - MSFT: 0.88s
  - AFL: 0.77s
  - BAC: 0.71s
  - JPM: 0.64s
  - AMT: 0.62s
  - AZO: 0.60s

### Phase 2 -- EDGAR fetch
- Total: 22.2s across 8 tickers
- Average per ticker: 2.78s
- Slowest 10 tickers:
  - JPM: 4.13s
  - BAC: 2.96s
  - AMT: 2.87s
  - MSFT: 2.76s
  - AFL: 2.62s
  - AAPL: 2.35s
  - O: 2.34s
  - AZO: 2.22s

### Phase 3 -- Calculate + plot
- Calculate (calculate_all_metrics/build_metrics_long/build_valuation_history/build_snapshot, whole batch, one run -- not decomposed per ticker, since doing so would mean calling these functions once per ticker instead of once for the batch, a change to how the calculation runs rather than pure instrumentation): 11.3s
- Plot: **skipped** (`write_charts=False`). No figures were built and no chart files were written. Nothing downstream depends on them -- the app renders from `data/app/*.parquet`, exported either way. Re-run with `run_full_refresh(write_charts=True)` to produce `figures/` again.

## Data quality flags

10 flags across 5 profiles.

### financial

- **thin** BAC `StockIssued`: 32 of 75 (43%) -- `python explore_tags.py BAC issuanceofcommon stockissuedduringperiodvalue saleofequity`
- **thin** JPM `StockIssued`: 2 of 74 (3%) -- `python explore_tags.py JPM issuanceofcommon stockissuedduringperiodvalue saleofequity`

### insurance_life

- **MISSING** AFL `Investments`: 0 of 74 (0%) -- `python explore_tags.py AFL investments`
- **thin** AFL `Goodwill`: 7 of 74 (9%) -- `python explore_tags.py AFL goodwill intangible`
- **thin** AFL `ShareBasedCompensation`: 27 of 74 (36%)

### reit

- **MISSING** AMT `GainLossOnSaleOfProperties`: 0 of 74 (0%)
- **thin** O `StockRepurchased`: 4 of 70 (6%) -- `python explore_tags.py O repurchase treasurystock buyback`
- **thin** O `PretaxIncome`: 24 of 70 (34%)

### retail

- **MISSING** AZO `DividendsPerShare`: 0 of 73 (0%) -- `python explore_tags.py AZO dividendspershare`

### standard

- **thin** AAPL `Goodwill`: 36 of 75 (48%) -- `python explore_tags.py AAPL goodwill intangible`
