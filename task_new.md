# Task: REIT Tag Coverage Scan (~28 tickers)

O is the reference ticker for the `reit` profile. FFO is computed from raw concepts
(`NetIncomeLoss_TTM + DepreciationAndAmortization_TTM − GainLossOnSaleOfProperties_TTM`), not
a reported FFO tag (REITs' own FFO disclosures use inconsistent, filer-specific non-GAAP
extension tags that don't generically fall back across companies). Two real tag-fallback bugs
were found and fixed on O itself before this batch started:

1. **`OtherNotesPayable` was removed from the `LongTermDebt` fallback list.** It looked like a
   reasonable fallback when `NotesPayable` had a reporting gap, but it measures a materially
   different, much smaller debt component (plausibly mortgage/seller-financing notes, not
   total unsecured notes) — using it silently understated O's debt by roughly 15x during that
   gap. **This is the single most important lesson for this batch**: do not add a fallback tag
   to `LongTermDebt` (or any REIT concept) just because it returns a plausible-looking number
   during a gap — verify its scale against the primary tag's own neighboring values first, the
   same discipline that caught this for O.
2. The project-wide `calculate_growth` date-alignment fix (already shipped, not part of this
   task) resolved a separate issue where reporting gaps caused positional YoY comparisons to
   silently span years instead of one — relevant here because REITs, like O, may have their own
   historical tagging gaps.

## Step 0 — Setup

```python
TICKER_PROFILES = {
    ...,
    # Net lease / diversified
    "WPC": "reit", "NNN": "reit",
    # Industrial / logistics
    "PLD": "reit",
    # Storage
    "PSA": "reit", "EXR": "reit", "CUBE": "reit",
    # Data centers
    "DLR": "reit", "EQIX": "reit",
    # Towers / digital infrastructure
    "AMT": "reit", "CCI": "reit", "SBAC": "reit",
    # Retail
    "SPG": "reit", "REG": "reit", "FRT": "reit", "KIM": "reit",
    # Residential
    "AVB": "reit", "EQR": "reit", "MAA": "reit", "ESS": "reit",
    "INVH": "reit", "UDR": "reit", "CPT": "reit",
    # Healthcare
    "WELL": "reit", "VTR": "reit", "DOC": "reit",
    # Office
    "BXP": "reit",
    # Hotels
    "HST": "reit",
    # Specialty
    "WY": "reit", "IRM": "reit",
}
```

**Verify this list against the current S&P 500 constituents before adding anything** — same
Step-0 discipline as every prior batch. This list was assembled from general REIT-sector
knowledge, not verified against the live index; confirm each ticker is current, correctly
named, and actually in the S&P 500 (some REITs are large and well-known but not
S&P-500-constituent — drop and note any that aren't).

`PROFILE_HIDDEN["reit"]` and `PROFILE_EXCLUDED_CONCEPTS["reit"]` stay as already set for O —
`pe_ratio`, `payout_ratio`, `income_yoy_growth`, `operating_margin`, `net_debt_to_ebitda`,
`ev_ebitda`, `capex_intensity`, `pfcf_ratio`, `fcf_margin` all hidden;
`OperatingIncomeLoss`/`Capex` excluded from expected concepts.

## Step 1 — Structural check: towers/digital infrastructure (AMT, CCI, SBAC) — investigate only

Cell towers and data centers are REITs by tax structure but economically closer to
infrastructure/utilities than to traditional property (leased equipment/land, less
straightforward "real estate depreciation," often significant non-real-estate D&A on
technical equipment). For these three (and consider EQIX/DLR too, which are data-center REITs
with similar equipment-heavy characteristics):

1. Check whether `DepreciationAndAmortization` for these tickers is dominated by real estate
   or by technical/equipment depreciation — if the latter, the FFO calculation (which assumes
   D&A add-back approximates real estate depreciation) may overstate FFO for these names.
2. Compare `ffo_margin` and `debt_to_equity` volatility/scale against the traditional
   property REITs in this batch (SPG, AVB, etc.) — do they look structurally different?
3. **Do not reassign these tickers yourself.** Report findings as a clearly separated
   recommendation — whether they'd be better served by a dedicated `reit_infrastructure`
   profile or a different FFO treatment — and leave them in `reit` for now. Same rule as
   every prior structural question in this project (CEG/VST/NRG, COST/WMT/TGT, etc.).

## Step 2 — Coverage scan

Run `check_data_quality` for each verified ticker. Flag anything below 50%, with the standard
`DividendsPerShare` non-payer exception — verify per ticker, though REITs are almost uniformly
dividend payers by tax-law requirement (must distribute ~90% of taxable income), so a
non-payer flag here would itself be worth double-checking as a possible data gap rather than
assuming it's a real non-payer.

## Step 3 — Known traps for this batch

- **`LongTermDebt` tag variance across REIT sub-types — verify per ticker, do not reuse O's
  exact tag set blindly.** REITs use a wide variety of debt instruments (mortgage notes,
  secured/unsecured notes, credit facilities, construction loans) and tag them
  inconsistently. For each ticker, check that whichever tag ends up winning the fallback
  actually represents *total* long-term debt at a scale consistent with the company's known
  size — apply the same scale-sanity check that caught `OtherNotesPayable`'s error on O. If a
  ticker's resolved `LongTermDebt` value looks implausibly small relative to its market cap
  or peer REITs of similar size, investigate before accepting it.
- **`GainLossOnSaleOfProperties` coverage.** Confirm the existing tag candidates
  (`GainLossOnSaleOfProperties`, `GainsLossesOnSalesOfInvestmentRealEstate`,
  `GainLossOnSaleOfPropertiesNetOfTax`, `GainLossOnDispositionOfRealEstate`) actually resolve
  cleanly for each ticker — if a ticker shows 0% coverage here, search for its actual tag
  rather than assuming the existing four-tag list is universal (O's own experience shows the
  first three guessed tags were wrong; only the plain, unsuffixed name worked).
- **FFO sanity check across the batch.** Compute `ffo_margin` for every ticker and look for
  implausible values (very high margins, negative FFO for a healthy-looking company, or huge
  swings) — cross-check any outlier against the same "is this a real corporate event or a
  tag/scope issue" discipline used throughout this project, rather than accepting or rejecting
  based on magnitude alone.
- **Non-pure-play REITs.** WELL, VTR (healthcare, often with operating/senior-living
  components beyond pure real estate) and HST (hotels, which involve operating businesses
  layered on real estate) may have `NetIncomeLoss` or `DepreciationAndAmortization` figures
  that mix real estate and operating-business economics in ways that distort the simple FFO
  formula. Flag any ticker where this looks like a real concern, same investigate-only rule
  as Step 1.
- **Reporting gaps, now safe by construction but still worth confirming.** The
  `calculate_growth` date-alignment fix should already handle any REIT-specific reporting gaps
  correctly — but if any ticker in this batch shows an unexpectedly large or masked growth
  value, confirm it traces to a real gap (and is being handled correctly) rather than
  assuming the fix covers every case without checking.

## Step 4 — Mode decisions, non-regression, coverage re-check

Same authorization, same non-regression discipline, same reporting format as every prior scan
task (extract all affected concepts for all cached tickers before/after, zero tolerance for
changes to previously-populated values, before/after coverage table).

## Output

One file, `reit_scan_report.md`: the ticker-list verification, the tower/infrastructure
structural findings (recommendation only, no reassignment), the coverage scan results, any
`LongTermDebt` scale-sanity findings per ticker, the FFO sanity check across the batch, the
non-pure-play REIT findings, the non-regression results, and the before/after coverage table.

No scratch scripts left behind. Do not reassign any ticker's profile, and do not add any
`LongTermDebt` fallback tag without verifying its scale against the primary tag's neighboring
values first — this is the single most important discipline carried over from O's own fix.