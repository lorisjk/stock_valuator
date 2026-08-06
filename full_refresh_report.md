# Full Refresh Report

## Run metadata

- Start: 2026-08-05T17:35:20
- End: 2026-08-05T17:36:11
- Total wall-clock time: 51.1s (0.9 min)
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
- Total: 23.0s across 8 tickers
- Average per ticker: 2.88s
- Slowest 10 tickers:
  - AFL: 3.79s
  - AMT: 3.74s
  - JPM: 3.25s
  - BAC: 3.08s
  - MSFT: 2.53s
  - AZO: 2.26s
  - AAPL: 2.22s
  - O: 2.16s

### Phase 2 -- yfinance fetch
- Total: 6.8s across 8 tickers
- Average per ticker: 0.85s
- Slowest 10 tickers:
  - AAPL: 1.44s
  - AFL: 1.02s
  - JPM: 0.82s
  - AMT: 0.76s
  - BAC: 0.73s
  - O: 0.71s
  - MSFT: 0.69s
  - AZO: 0.67s

### Phase 3 -- Calculate + plot
- Calculate (calculate_all_metrics/build_metrics_long/build_valuation_history/build_snapshot, whole batch, one run -- not decomposed per ticker, since doing so would mean calling these functions once per ticker instead of once for the batch, a change to how the calculation runs rather than pure instrumentation): 11.5s
- Plot (per ticker, all three charts): total 7.6s across 8 tickers, average 0.95s/ticker
- Slowest 10 tickers (plotting):
  - AAPL: 2.80s
  - MSFT: 0.89s
  - AZO: 0.83s
  - AFL: 0.68s
  - BAC: 0.66s
  - JPM: 0.65s
  - AMT: 0.56s
  - O: 0.54s

## Data quality flags

12 flags across 5 profiles.

### financial

- **thin** BAC `StockIssued`: 32 of 75 (43%) -- `python explore_tags.py BAC issuanceofcommon stockissuedduringperiodvalue saleofequity`
- **thin** JPM `StockIssued`: 2 of 73 (3%) -- `python explore_tags.py JPM issuanceofcommon stockissuedduringperiodvalue saleofequity`

### insurance_life

- **MISSING** AFL `ShareBasedCompensation`: 0 of 73 (0%)
- **MISSING** AFL `Investments`: 0 of 73 (0%) -- `python explore_tags.py AFL investments`
- **MISSING** AFL `StockIssued`: 0 of 73 (0%) -- `python explore_tags.py AFL issuanceofcommon stockissuedduringperiodvalue saleofequity`
- **thin** AFL `Goodwill`: 7 of 73 (10%) -- `python explore_tags.py AFL goodwill intangible`

### reit

- **MISSING** AMT `GainLossOnSaleOfProperties`: 0 of 74 (0%)
- **thin** O `StockRepurchased`: 2 of 69 (3%) -- `python explore_tags.py O repurchase treasurystock buyback`
- **thin** O `PretaxIncome`: 23 of 69 (33%)

### retail

- **MISSING** AZO `StockIssued`: 0 of 73 (0%) -- `python explore_tags.py AZO issuanceofcommon stockissuedduringperiodvalue saleofequity`
- **MISSING** AZO `DividendsPerShare`: 0 of 73 (0%) -- `python explore_tags.py AZO dividendspershare`

### standard

- **thin** AAPL `Goodwill`: 36 of 75 (48%) -- `python explore_tags.py AAPL goodwill intangible`
