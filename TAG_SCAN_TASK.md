# Task: Structural Fix — Unified Per-Date Priority Merge

## The root problem (same bug, two disguises)

`fallback_then_sum` (used by `LongTermDebt`) and `fallback_sum` (used by
`DepreciationAndAmortization`, base and `financial` override) both try to do
"prefer clean tags, fall back to summing components" — but neither actually
does a clean per-date priority merge:

- `fallback_then_sum`: `tags` always wins over `sum_tags` for any date, no
  matter where a tag sits in the `tags` list. A tag appended "last" in `tags`
  is only last *relative to other tags* — it still unconditionally beats the
  `sum_tags` result. This is exactly what caused Run-2's apply task to revert
  the `LongTermDebtAndCapitalLeaseObligations*` additions (331 regressions).
- `fallback_sum`: the fallback to `fallback_sum_tags` only triggers when the
  *entire* primary-`tags` series is empty for that ticker — an all-or-nothing
  gate per ticker, not per date. This structurally blocks every candidate from
  ever helping a ticker (MTB, BAC, NTRS, TER, TRMB, KEYS) that already has
  *some* primary-tag coverage, regardless of what the new tag's data actually
  looks like.

Both are solved by the same fix: one ordered list of "sources" (a source is
either a single tag or a sum-of-tags group), merged **per date**, first source
in the list with a value for that date wins — full stop, no tier distinction
between "tags" and "sums."

## Part A — Implement the new mode

Add a new mode, `priority_merge`, to `extract_with_mode` in `parse_edgar.py`.
Do not remove the existing `fallback`, `sum`, `fallback_sum`, `fallback_then_sum`
code paths — other concepts may still use plain `fallback`/`sum` and should be
untouched by this task.

Config shape for a concept using the new mode:

```python
"ConceptName": {
    "sources": [
        {"type": "tag", "tag": "SomeTag"},
        {"type": "tag", "tag": "AnotherTag"},
        {"type": "sum", "tags": ["ComponentA", "ComponentB"]},
        {"type": "tag", "tag": "LowConfidenceTag"},
    ],
    "point_in_time": True,  # or False — same as today, one flag for the whole concept
    "mode": "priority_merge",
},
```

Algorithm — implement this exactly, it's a straightforward generalization of
the existing `extract_merged_values`:

```python
def extract_priority_merge(us_gaap_data, sources, period, is_point_in_time):
    merged = {}
    for source in sources:
        if source["type"] == "tag":
            concept_data = us_gaap_data.get(source["tag"])
            if concept_data is None:
                continue
            values = (extract_annual_values if period == "annual" else extract_quarterly_values)(
                concept_data, is_point_in_time=is_point_in_time
            )
        elif source["type"] == "sum":
            values = extract_summed_values(
                us_gaap_data, source["tags"], is_point_in_time=is_point_in_time, period=period
            )
        else:
            raise ValueError(f"unknown source type: {source['type']}")

        for v in values:
            if v["end"] not in merged:
                merged[v["end"]] = v

    return sorted(merged.values(), key=lambda v: v["end"])
```

Order in the list is priority, full stop — a `sum` step is not special-cased,
it just occupies whatever position it's given, and is skipped for any date
already claimed by an earlier source.

## Part B — Migrate LongTermDebt and DepreciationAndAmortization, staged

Do this as **two separate, verified steps** — do not add new tags in the same
step as the mode migration. This lets a regression get traced to "the merge
logic changed" vs. "a new tag was added," which matters if anything breaks.

### Step B1 — Pure refactor, zero new tags, must be byte-identical to today

Rewrite these three configs to use `sources`/`priority_merge`, preserving the
*exact current effective priority* — same tags, same order, sum group placed
exactly where `sum_tags`/`fallback_sum_tags` currently sits (i.e., right after
all the named tags, nothing added yet):

- `CONCEPT_CANDIDATES["LongTermDebt"]`: all current `tags` entries in their
  current order, each as a `{"type": "tag", ...}`, followed by one
  `{"type": "sum", "tags": [...]}` using the current `sum_tags` list.
- `CONCEPT_CANDIDATES["DepreciationAndAmortization"]`: current `tags` entries,
  then a `sum` step with the current `fallback_sum_tags`.
- `PROFILE_CONCEPT_OVERRIDES["financial"]["DepreciationAndAmortization"]`: same
  pattern with its current tags/fallback_sum_tags (the one added in the
  previous task, currently inert — migrate it too, for consistency).

**Verification (must pass before Step B2 starts):** for every ticker with
cached SEC data (check `cache/*_company_info.json`, plus anything listed in
`TICKER_PROFILES` even if not yet cached — fetch if needed), extract
`LongTermDebt` and `DepreciationAndAmortization` under the **old** config and
the **new** `priority_merge` config, and diff every `(ticker, end)` value.
This must come back with **zero differences** — it's a pure restructuring, the
output must be identical. If anything differs, the migration has a bug; fix it
before proceeding, don't paper over it by adjusting the "expected" values.

### Step B2 — Now add the previously-blocked tags, as new lowest-priority sources

Only after B1 is proven identical, append these as new `{"type": "tag", ...}`
entries **after** the `sum` step (i.e., last priority — they fire only where
neither the named tags nor the sum has data for that date):

- `LongTermDebt.sources`: append `LongTermDebtAndCapitalLeaseObligations`,
  then `LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities`.
- `DepreciationAndAmortization.sources` (base): append `AdjustmentForAmortization`,
  then `FiniteLivedIntangibleAssetsAmortizationExpense`.
- `financial` D&A override `.sources`: append `DepreciationNonproduction`,
  `DepreciationPremisesAndEquipment`, `CapitalizedComputerSoftwareAmortization`
  (the MSR tag from the previous task should already be present — keep it,
  positioned last as before).

**Verification (mandatory, same non-regression discipline as the previous
task):** re-run the full diff across the same ticker universe. Every
previously-populated `(ticker, concept, end)` value must be unchanged. Only
previously-null values may now be populated. If any previously-populated value
changes, that specific tag's position or inclusion is wrong — remove it and
log why, don't force it through.

## Part C — Re-check coverage on the still-flagged tickers

Re-run `check_data_quality` on the tickers that were still gapped after the
previous task (the 36 unresolved from `run2_apply_report.md`'s Part D table,
excluding CRWD/NTRS/SYF which are already resolved). Produce a before/after
coverage table like the previous report's Part D, plus a short note on which
tickers' `LongTermDebt`/`DepreciationAndAmortization` gaps are now closed or
meaningfully improved thanks to the fixed per-date gating.

## Part D — Cleanup (optional, only if safe)

If, after B1+B2, nothing in the codebase still references the old
`fallback_then_sum` or `fallback_sum` modes (check the full `config.py` for
any other concept using them — do not assume LongTermDebt/D&A are the only
ones without checking), it's fine to leave the old mode implementations in
`extract_with_mode` as dead code rather than removing them — do not delete
code as part of this task unless you are certain nothing depends on it.
Removing dead code is not the goal here; correctness and non-regression are.

## Output

One file, `priority_merge_report.md`: what the new mode does, confirmation
that B1 was byte-identical (with the diff count, should be 0), what was added
in B2 and the regression check result (should be 0 regressions), the Part C
before/after table, and any open questions. No scratch scripts left behind.