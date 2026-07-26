# Task: Backlog Cleanup — net_debt_to_ebitda Guard, GLW Capex Error, FIX Restatement

Three independent, previously-logged, low-to-medium-priority items. Each gets its own
investigation and fix (or documented non-fix) — do not let one influence how you treat
another; they have different root causes.

---

## PART A — `net_debt_to_ebitda`: the remaining 33 unguarded cases

### Context

The Tier-1 ratio guard task fixed 20 of 53 confirmed `net_debt_to_ebitda` explosions using an
absolute EBITDA-magnitude floor (`min_denominator_abs`). The remaining 33 needed a different
mechanism — the absolute floor doesn't fit them, per that task's own finding, but no fix was
built for them at the time.

### Step 1 — Characterize the remaining 33 before designing anything

Pull the 33 still-unguarded explosion cases (re-derive them if the original list isn't
still on hand: compute `net_debt_to_ebitda` across the full cached universe, flag implausible
magnitudes, and subtract the 20 already fixed). For each, look at the actual `net_debt` and
`ebitda` values driving the explosion — is `ebitda` moderately small (not near-zero, just
small relative to a large `net_debt`), or is this a different shape of problem entirely (e.g.
`net_debt` itself unusually large from a specific event)? Don't assume the fix is "the same
mechanism, different threshold" until you've looked.

### Step 2 — Design and calibrate a scale-relative guard

If Step 1 confirms these are genuinely a "small-EBITDA-relative-to-scale" problem (not caught
by an absolute floor because the absolute floor was tuned to the first 20's specific
magnitudes), build a relative guard analogous to the `roe`/`debt_to_equity` fix from the same
Tier-1 task — compare `ebitda`'s magnitude against a scale reference (candidates: `Revenue_TTM`,
or `net_debt` itself, whichever the real data supports better — state your reasoning) rather
than an unrelated absolute dollar figure. Calibrate the threshold from where these 33 cases'
`ebitda`/scale-reference ratio actually clusters, the same marginal-return-curve method used
throughout this project — don't reuse a number from a different guard without re-deriving it
against this specific data.

### Step 3 — Verify no over-masking

Confirm the new guard doesn't mask legitimate, real net-debt-to-EBITDA readings for companies
with genuinely thin (but real, not near-zero) margins — spot-check a few plausible candidates
(e.g. a capital-intensive but currently-thin-margin business) before finalizing.

### Step 4 — Non-regression (full universe, base metric)

Same rule as every prior guard fix: extract `net_debt_to_ebitda` for every cached ticker
before/after, confirm only the confirmed-explosion cases newly mask, report the full list.

---

## PART B — GLW Capex 2011-03-31 raw-value error

### Context

Flagged in the decumulation positive-outlier scan as "a single, never-restated, directly-filed
value ($100,000,000,000) — implausible on its face for Corning at any scale... recommended for
a separate, dedicated data-quality investigation," out of scope at the time.

### Step 1 — Investigate the raw fact directly

Pull GLW's raw XBRL fact(s) for `Capex`'s underlying tag(s) around 2011-03-31. Check: is this
a single anomalous value with no corroborating restatement (as previously assumed), or does a
later filing correct it (making it a `_KNOWN_BAD_FACTS`-style case after all)? Check the
`unit`/`decimals` attributes too — a scale error (e.g. reported as if in different units) is
plausible for a single-filing typo the same way `SharesOutstanding`'s multi-filer bug was, just
without a second, correcting filing to compare against.

### Step 2 — Fix appropriately, or document as unfixable

- If a later filing corrects it: use `_KNOWN_BAD_FACTS`, same as every prior case.
- If no correction exists anywhere but the value is clearly implausible (a $100B capex quarter
  for a company of GLW's size and era is not plausible under any real scenario) and a sane
  original scale can be inferred with confidence (e.g. dividing by an obvious factor lands on a
  number consistent with GLW's neighboring quarters) — check whether this is safe to correct
  or whether it should simply be dropped/masked with no replacement value. Prefer masking over
  guessing a corrected value unless the evidence for a specific correction is strong.
- Report your reasoning either way. A single-fact, no-corroboration case is a different
  evidentiary situation than every prior fix in this project (which all had two competing
  filed values to choose between) — be explicit about that difference in the writeup.

### Step 3 — Non-regression

Confirm the fix (or mask) affects only this one `(GLW, Capex, 2011-03-31)` fact, nothing else.

---

## PART C — FIX (Comfort Systems USA) unexplained restatement

### Context

Flagged in the decumulation scope-mismatch report as an ~80% jump within a two-month filing
window with no known corporate event identified at the time — noted as "possibly a separate,
not-yet-investigated error," explicitly deferred.

### Step 1 — Investigate

Pull FIX's raw facts around the flagged dates. Identify the exact concept, values, and filing
dates involved. Search for a real corporate event around that window (acquisition, divestiture,
accounting restatement, segment reclassification) that could explain an 80% change — Comfort
Systems has a history of frequent, smaller acquisitions (a "roll-up" M&A strategy), so check
whether this could be a real, if unusually large, single acquisition effect before assuming
it's a data error.

### Step 2 — Classify and act accordingly

- If a real corporate event explains it: document as a confirmed scope-related event, no fix
  needed (same as the other real-event cases already documented and left alone throughout this
  project).
- If it shows the same restatement signature as this project's known bug classes (two
  differently-scoped filed values for the same period): apply the appropriate existing
  mechanism (`_KNOWN_BAD_FACTS` or the scope-mismatch outlier mechanisms), following the same
  evidence standard as every prior fix.
- If neither explanation holds with confidence: report it as a confirmed-but-unexplained
  anomaly and leave it untouched, per this project's "log as ambiguous rather than guess" rule.

### Step 3 — Non-regression

Confirm any fix applied touches only the specific confirmed fact(s), nothing else.

---

## Overall non-regression (all three parts combined)

Run one final full-universe check across all cached tickers, confirming the combined effect of
Parts A, B, and C together touches only the specific tickers/concepts/dates each part
individually confirms — no cross-contamination between the three unrelated fixes.

## Document

One combined entry (or three sub-entries) in `bugfixed_update_history.md` covering all three
parts, following the existing style — what was found, what was fixed or left as a documented
non-fix, and why.

## Output

One file, `backlog_cleanup_report.md`, with three clearly separated sections (A, B, C) each
containing its own investigation findings, fix (or documented non-fix) and reasoning, and the
combined non-regression results at the end.

No scratch scripts left behind. Keep the three parts' changes clearly separated in the report
even though they may touch the same files.