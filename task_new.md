# Task: Airline Batch Scan (2 tickers: DAL, UAL)

LUV is the reference ticker for the `airline` profile. Confirmed on LUV: a real ASC 842
lease-accounting scope break (`debt_to_equity` jumps from ~0.35 to ~1.15 around 2019-2020,
operating lease liabilities coming onto the balance sheet — a real accounting-standard change,
not a bug) and a genuine multi-year negative `FCF_TTM` (2022-Q4 onward, tied to Boeing 737 MAX
delivery delays and LUV's 2025 operating-model changes) that correctly triggers the existing
`pfcf_ratio > 0` guard. No new tags/concepts needed — `airline` runs on the base tag set, only
hidden-metric branching differs.

## Step 0 — Setup

```python
TICKER_PROFILES = {
    ...,
    "DAL": "airline", "UAL": "airline",
}
```

`PROFILE_HIDDEN["airline"]` stays as already set for LUV — `debt_to_equity`,
`net_debt_to_ebitda`, `operating_margin`, `pfcf_ratio`, `rule_of_40` all currently visible
pending this batch's findings.

## Step 1 — Confirm the ASC 842 scope break for DAL and UAL

Apply the same same-filing-date, similar-magnitude-jump detection method already used
throughout this project to `LongTermDebt`/`debt_to_equity` for both tickers around 2019-2020.
Confirm each shows the same real, expected lease-liability-onto-balance-sheet jump — don't
assume it transfers from LUV without checking, since DAL/UAL's own lease footprints (owned vs.
leased fleet mix) differ from LUV's.

## Step 2 — Loyalty-program monetization scope check

Both DAL (SkyMiles) and UAL (MileagePlus) have done large loyalty-program financing/monetization
transactions (securitizations, partial stake sales tied to co-brand credit card deals) in recent
years. Check whether either transaction shows up as a `Revenue` or `OperatingIncomeLoss`
scope-break signature (same detection method as Step 1) — a large one-time financing-related
gain or a revenue-recognition change tied to these deals could look like a real jump/dip that
needs the same "real event, not a bug" documentation as every other confirmed scope break in
this project, or could reveal an actual tag-scope mismatch if the pipeline picks up gross deal
proceeds instead of recurring revenue. Investigate and report either way — don't assume either
outcome.

## Step 3 — Coverage scan

Run `check_data_quality` for both tickers. Flag anything below 50%, with the standard
`DividendsPerShare` non-payer exception — verify per ticker (both DAL and UAL suspended
dividends during COVID; confirm current status directly rather than assuming from general
industry reputation).

## Step 4 — Known traps

- **`OperatingIncomeLoss` fragility** — LUV was clean (relatively simple, single-segment
  operations). DAL and UAL both have more complex operating structures (cargo, MRO/maintenance
  services, and the loyalty program itself sometimes reported with segment detail) — check each
  independently rather than assuming LUV's clean outcome transfers.
- **COVID-era negative equity / extreme guard stress-test.** DAL and UAL both took on
  substantial government support (payroll support program) and debt during 2020-2021 and may
  show more severe equity/earnings distortion than LUV (which, per the anchor test, is
  historically the industry's most consistently profitable carrier). Confirm the existing
  near-zero/negative-equity guards and `min_base_ratio` growth guard handle both tickers'
  2020-2021 windows correctly rather than assuming they do.
- **Multi-year negative FCF, same discipline as LUV.** Check whether DAL/UAL show a similar
  negative-FCF stretch (fleet renewal, MAX delays affect the whole industry, not just LUV) and
  confirm the `pfcf_ratio > 0` guard behaves the same correct way — don't treat a masked chart
  as a data problem without checking the underlying FCF sign first, the same verification done
  for LUV.
- **Scope breaks beyond loyalty programs** — check for any other major restructuring
  (bankruptcy history, fleet-related divestitures) using the established detection method.

## Step 5 — `rule_of_40` and `pfcf_ratio` decisions, from real data across the batch

Compute `rule_of_40` for all 3 tickers (LUV + DAL + UAL) and report where each sits relative to
40% over full history — LUV alone showed mostly low readings with a COVID-recovery-driven spike
to ~180%, similar to the "temporary artifact, not sustained quality" pattern seen in several
other cyclical profiles. Recommend hide-profile-wide vs. leave-visible with the supporting data.
Also confirm whether `pfcf_ratio`'s masking behavior (real but structural, per LUV) looks
consistent across all three tickers, or whether it's worth flagging as a profile-wide
characteristic in documentation.

## Step 6 — Mode decisions, non-regression, coverage re-check

Same authorization, same non-regression discipline, same reporting format as every prior scan
task (extract all affected concepts for all cached tickers before/after, zero tolerance for
changes to previously-populated values, before/after coverage table).

## Output

One file, `airline_scan_report.md`: the ASC 842 confirmation for both tickers, the
loyalty-program scope-check findings, the coverage scan results, the `OperatingIncomeLoss`
findings per ticker, the COVID-era guard verification, the negative-FCF/`pfcf_ratio` findings,
the `rule_of_40` recommendation with supporting data, the non-regression results, and the
before/after coverage table.

No scratch scripts left behind. Do not reassign any ticker's profile, and do not touch any
concept unrelated to `airline`'s metric set.