# Audit: `_normalize_scale_outliers` — the Last Uncorroborated Guesser

Input: section 8 of `split_normalisation_report.md`, which shipped a corroborated split
normaliser and left this one function still choosing a numeric correction with nothing
independent to check against.

**Headline: the sweep is right where it can be checked — 253 of 263 testable rescalings, 96%.**
That is the opposite of what the split normaliser turned out to be (17% right), and it changes
the appropriate remedy: a gate that rejects the refuted cases, not a replacement. Ten rescalings
on one ticker were corrupting correct values and now stop. The measured downstream effect of
that correction is small and is reported as such.

Measured over all 501 active tickers from the local EDGAR cache, with one cached yfinance pass
supplying the corporate-action feed the split basis needs.

---

## 1. Step 1 inventory

### Which concepts it touches: exactly one

`_SCALE_CORRECTED_CONCEPTS = {"SharesOutstanding"}`, checked in code and confirmed by running it.
The sweep is **not** broader than the split report assumed, so the scope of everything below is
one concept.

### How much it does

**279 rescalings across 70 tickers**, out of 32,061 `SharesOutstanding` rows — 0.87%.

> The split report quoted 350 rows across 79 tickers. That measurement predates the ordering fix
> shipped in the same task. Applying the split basis **before** the sweep removed 71 of them, all
> Chipotle: its pre-split counts are 50x low, and the sweep — which knows only powers of ten —
> used to "fix" them by 100x. Those rows now arrive already on the right basis and the sweep
> leaves them alone. 279 is the current figure.

### Factor distribution

| factor | rescalings |
|---|---:|
| 100 | 12 |
| 1,000 | 192 |
| 100,000 | 2 |
| 1,000,000 | 70 |
| 10,000,000 | 3 |

### Verdict on the distribution: **not informative, for the same reason as the split factors**

Every factor is a power of ten because `_SCALE_UP_FACTORS` contains nothing else. A clean
power-of-ten ratio is the algorithm's vocabulary, not evidence that a unit error occurred. The
concentration at 1,000 and 1,000,000 matches how filers actually scale tables ("in thousands",
"in millions"), which is a weak positive signal — but it is equally what you would see if the
function were wrong, since those are the only factors it can reach with its 0.5-dex match
tolerance. The distribution has to be treated as uninformative and the rescalings checked
individually.

### Upward vs downward: **279 upward, 0 downward — by construction**

```python
if own_log > anchor_log:
    continue          # _sweep_scale_outliers: values above the anchor are never touched
```

The sweep can only raise an implausibly small value. It **cannot** correct an implausibly large
one, so Agilent's 406 is in scope and **AIG's 130-trillion row is not**. Section 7 covers what
that leaves behind.

### One correction to the brief's framing

The sweep is described as using "the same anchor-proximity idea" as the deleted split normaliser.
That is only half right, and the difference matters. `_normalize_series` compared every value to
`values.iloc[-1]`, the newest value — a global pull toward today. `_sweep_scale_outliers` seeds
its anchor from the median of the first five values in sweep order and then **re-anchors on every
accepted value**, so it compares each value to its running neighbours. It also runs forward and
backward and requires the two to agree where both fire. It is a local outlier detector, which is
a substantially better instrument — and the audit result reflects that.

---

## 2. Corroboration sources

### Rejected: the XBRL fact's own unit or scale attribute

The SEC companyfacts API returns exactly these fields per fact:

```
accn, end, filed, form, fp, fy, start, val
```

**No `decimals` attribute**, and the unit key is `shares` for correct and mis-scaled values
alike. Nothing here distinguishes 406 from 406,000,000. Dead end — recorded so the next
investigation does not repeat it.

### Rejected as circular: the neighbouring periods

"A single period 1,000x out of line with its neighbours is an error" is precisely the sweep's own
criterion. Using it as corroboration would confirm every proposal by construction.

### Used: the filer's own restatement of the same period

Directly reusable from the split task. A genuine mis-scaling is usually corrected in a later
filing, and the ratio is a clean power of ten:

```
COHR 2019-03-31   filed 2019-05-09 = 65,701,000      filed 2020-05-11 = 65,701
LUV  2010-06-30   filed 2010-08-02 = 746,000,000     filed 2011-08-05 = 746
```

A variant is needed for filings that scale **everything**: Atmos Energy's 2011-02-09 filing tags
both the share count (92,509) and net income (93,330) in thousands, so the two are mutually
consistent and the arithmetic test below passes. The tell is that the *net income* for that same
period is reported as 93,330,000 in a later filing. Restatement of either quantity by the
proposed factor counts as support.

### Used: the reporting filing's own EPS arithmetic

`net income / share count` must equal reported diluted EPS, and all three appear in the same
filing. Keyed on `(accn, start, end)` so the three always describe one period from one filing,
the test detects a scale error and nothing else — no split basis, no unit convention, no
restatement history can leak in.

**Getting this wrong first was instructive.** A first pass matched EPS to the share count by
period alone, across filings. On NVDA it reported a 25x inconsistency that was really the
difference between a 2009-basis EPS and a share count restated for the 2021 and 2024 splits — an
apparent scale error invented entirely by mixing bases. A second pass matched by accession but
not by period, and paired quarterly net income with year-to-date EPS, spreading the implied error
over 2.2–2.9 instead of landing on 3.0. Only the full `(accn, start, end)` key gives a clean
result: after it, the implied errors cluster at exactly 3.00 (110 rows) and 6.00 (48 rows).

---

## 3. Classification

| class | rescalings | share |
|---|---:|---:|
| **corroborated error** | **253** | 90.7% |
| **contradicted** | **10** | 3.6% |
| **no evidence** | **16** | 5.7% |

Of the 263 rescalings with any evidence at all, **253 are right — 96%.**

Both sources agree far more often than not: 115 rescalings are supported by restatement *and*
arithmetic, 121 by arithmetic alone, 17 by restatement alone.

### The contradicted list — all ten, all one ticker

| ticker | period | filed | as filed | the sweep made it | implied error |
|---|---|---|---:|---:|---:|
| EXE | 2017-12-31 | 2021-02-02 | 4,529,000 | 452,900,000 | −0.05 |
| EXE | 2018-12-31 | 2021-03-01 | 4,546,000 | 454,600,000 | +0.12 |
| EXE | 2019-03-31 | 2020-05-11 | 6,902,000 | 690,200,000 | −0.16 |
| EXE | 2019-06-30 | 2020-08-10 | 8,141,000 | 814,100,000 | +0.06 |
| EXE | 2019-09-30 | 2020-11-09 | 8,492,000 | 849,200,000 | −0.11 |
| EXE | 2019-12-31 | 2022-02-24 | 8,325,000 | 832,500,000 | −0.07 |
| EXE | 2020-03-31 | 2021-05-13 | 9,753,000 | 975,300,000 | −0.00 |
| EXE | 2020-06-30 | 2021-08-10 | 9,779,000 | 977,900,000 | −0.00 |
| EXE | 2020-09-30 | 2021-11-02 | 9,780,000 | 978,000,000 | −0.00 |
| EXE | 2020-12-31 | 2023-02-22 | 9,773,000 | 977,300,000 | −0.00 |

Every implied error is ≈ 0: the filings' own arithmetic says these values are correct as filed.

**Expand Energy is the previous task's loose end reappearing from the other side.** Chesapeake
did a 1:200 reverse split in December 2020, restated its history, and emerged from bankruptcy
with about 9.8 million shares. Against a series that used to run at 1.4 billion, the restated
counts look like an outlier by two orders of magnitude, and the sweep obligingly multiplied them
by 100. The split investigation classified EXE as **no evidence** because its price history
begins 2021-02-10 — after the reverse split — so the corporate-action feed cannot see it. One
ticker, two mechanisms, both misled by the same missing feed coverage.

### The no-evidence list — all sixteen

| ticker | periods | as filed | factor |
|---|---:|---:|---:|
| A | 2007-10-31, 2009-01-31, 2009-04-30, 2010-01-31 | 406 / 352 / 344 / 354 | 1,000,000 |
| ARE | 2013-06-30 | 66,973 | 1,000 |
| EXE | 2019-02-01 | 3,600,000 | 100 |
| GEN | 2017-09-29 | 619,633 | 1,000 |
| MPWR | 2010-09-30 | 37,727 | 1,000 |
| NEE | 2008-06-30 | 403 | 1,000,000 |
| ROL | 2014-06-30, 2014-09-30 | 218,813 / 218,700 | 1,000 |
| VICI | 2016-12-31, 2017-09-30 | 1,000 | 100,000 |
| VTRS | 2020-03-29, 2020-06-28, 2020-09-27 | 100 | 10,000,000 |

Inspected individually against what the companies are: 15 of the 16 are obviously right —
Agilent really had ~350–400m shares, Alexandria ~67m, Gen Digital ~620m, Monolithic Power ~37m,
NextEra ~403m (×4 again for its 2020 split), Rollins ~219m before its splits. The exception is
**EXE 2019-02-01**, which is the eleventh member of the contradicted group and lands here only
because that odd period end carries no EPS triple to test with.

---

## 4. The no-evidence default: keep rescaling

**Decision: rescale when there is no evidence; stop only where the evidence contradicts.** This
is the *opposite* default from the split task, and the reasons are measurable rather than
principled.

1. **The base rate is inverted.** The split normaliser was 17% right where testable, so its
   untested cases were most likely wrong. This sweep is **96%** right where testable, so its
   untested cases are most likely right. Suspending it on no evidence would trade 15 correct
   corrections for 1.
2. **The asymmetry the brief names is real and it points the same way.** An uncorrected unit error
   is *loud*: Agilent at 406 shares gives a market cap of about $16,000 and an EPS in the hundreds
   of thousands of dollars — a reader spots it instantly. A wrong split factor was *quiet*: a
   2x-wrong share count produces a P/E that looks perfectly ordinary. Where the failure is loud,
   the cost of a rare wrong correction is bounded by being visible; where it is quiet, it is not.
3. **The class is tiny either way.** 16 rows is 5.7% of the rescalings and **0.05% of all 32,061**
   share-count rows.

**The third option — drop or flag rather than pass through — was considered and rejected here,
and the reason is worth recording:** the evidence I have does not identify *which* number carries
a scale inconsistency. `net income / shares ≠ EPS` is symmetric; it fires just as hard when the
net income is tagged in millions and the share count is right. Measured across the universe, 47
periods on 12 tickers show a ≥100x inconsistency after the pipeline, and inspection shows most of
them — HAL, HIG, CTVA, TMO — have **correct** share counts and a differently-scaled net income.
A rule that dropped rows on this signal would delete more good data than bad. Dropping needs a
detector that names the guilty quantity; section 7 describes one.

---

## 5. The change

`build_dataframe` now runs `_corroborated_scale_correction` in place of the bare sweep. The
sweep still *proposes* — it is a good local outlier detector — and each proposal is then checked
against the two sources. A proposal is dropped only when the filing's own arithmetic **refutes**
it. No evidence means the proposal stands, per section 4.

```
raw facts -> extract -> split basis -> scale sweep -> corroboration gate -> facts
```

Placement is unchanged from the split task's ordering fix: split basis first, unit scale second.

---

## 6. Step 4 — non-regression, all 501 tickers

### Facts

```
rows 511,464 -> 511,464   appeared=0   disappeared=0   changed=10
```

Every changed row, in full:

| ticker | period | before | after |
|---|---|---:|---:|
| EXE | 2017-12-31 | 452,900,000 | 4,529,000 |
| EXE | 2018-12-31 | 454,600,000 | 4,546,000 |
| EXE | 2019-03-31 | 690,200,000 | 6,902,000 |
| EXE | 2019-06-30 | 814,100,000 | 8,141,000 |
| EXE | 2019-09-30 | 849,200,000 | 8,492,000 |
| EXE | 2019-12-31 | 832,500,000 | 8,325,000 |
| EXE | 2020-03-31 | 975,300,000 | 9,753,000 |
| EXE | 2020-06-30 | 977,900,000 | 9,779,000 |
| EXE | 2020-09-30 | 978,000,000 | 9,780,000 |
| EXE | 2020-12-31 | 977,300,000 | 9,773,000 |

| check | result |
|---|---|
| no row appeared or disappeared | ok |
| only `SharesOutstanding` changed | ok |
| every change reverses a x100 rescaling, nothing else | ok |
| **anchor invariant**: newest `SharesOutstanding` unchanged, date and value, for every ticker | **ok — 498 of 498** |
| no change lands on any ticker's newest period | ok |

The current snapshot is therefore untouched — verified, not assumed.

### Independent plausibility check

The derived `EPS_TTM_CALC` is what the correction feeds, and the filer publishes the answer:

| EXE FY2020 | value |
|---|---:|
| `EPS_TTM_CALC` before | **−9.96** |
| `EPS_TTM_CALC` after | **−996.01** |
| **Chesapeake's reported diluted EPS, filed 2021-03-01** | **−998.26** |

The corrected figure lands within 0.2% of the filed number; the difference is the pipeline's
period-end share count against the filing's weighted average. The pre-fix figure was out by
exactly 100x. The same holds for FY2019 (reported −49.97 restated; before −0.37, after −37.00).

### Downstream, reported honestly

| frame | changed |
|---|---:|
| `facts` — `SharesOutstanding` | 10 |
| `facts` — `EPS_TTM_CALC` | 10 |
| `metrics_long` (all metrics, all tickers) | **0** |
| `valuation_history` (all multiples) | **0** |
| 5-year rolling means (all seven) | **0** |

**The correction does not reach a single chart, and it is worth saying so plainly.** EXE's price
history starts 2021-02-10, so no market capitalisation exists for 2017–2020 and every multiple
for those quarters was already blank. `payout_ratio`, the one metric that would consume
`EPS_TTM_CALC` without a price, is empty because Chesapeake paid no dividend in those quarters.
The measurable effect is confined to the `EPS_TTM_CALC` series in `facts`, which the app's Data
tab shows and nothing else consumes.

That is a real but modest outcome, and it does not diminish the audit: the value here is knowing
that the remaining 253 corrections are evidence-backed, and that the mechanism can no longer
corrupt a correct value the way it did for ten quarters of Expand Energy.

### Re-measured flags

| flag | before | after | delta |
|---|---:|---:|---:|
| `share_count_jump_flag` | 744 | 744 | 0 |
| `buyback_distortion_flag` | 644 | 644 | 0 |
| `inorganic_contaminated` | 1,016 | 1,016 | 0 |
| `low_tax_rate_flag` | 4,196 | 4,196 | 0 |
| coverage flags (all concepts) | 743 | 743 | 0 |

No flag moves. EXE's corrected quarters do not cross the 15% share-count jump threshold relative
to their neighbours — the whole 2017–2020 stretch shifts by the same factor.

### The two named cases

- **Agilent's 406** (2007-10-31, plus 352 / 344 / 354): **still corrected** to 406,000,000. It is
  in the no-evidence class and the default keeps it, which is the intended design.
- **AIG's 130,248,736,000,000** (2008-06-30): **untouched, before and after.** The sweep is
  upward-only, so it never had this row in scope; nothing in this change alters that. See below.

---

## 7. Deliberately not fixed

**Downward scale errors are outside the sweep entirely.** Five periods on four tickers carry a
share count that is provably 1,000x or more too large and pass straight through:

| ticker | period | value | the company's actual count |
|---|---|---:|---:|
| AIG | 2008-06-30 | 130,248,736,000,000 | ~2.7bn |
| SHW | 2007-12-31 | 130,924,690,000 | 122,814,241 |
| SHW | 2008-09-30 | 118,183,353,000 | 116,902,299 |
| TFC | 2008-06-30 | 549,758,000,000 | ~549m |
| ARE | 2011-03-31 | 54,967,755,000 | ~55m |

Sherwin-Williams supplies the cleanest possible evidence: **the same accession** that reports
`WeightedAverageNumberOfDilutedSharesOutstanding = 130,924,690,000` also reports
`CommonStockSharesOutstanding = 122,814,241`. One filing, two share counts, a factor of 1,000
apart. That within-accession disagreement is a **directional** detector — it names which tag is
wrong — and it is what a downward correction or a principled row-drop would need. Building it is
a new capability rather than an audit of an existing one, so it is recorded here rather than
attempted. The consolation is that these values fail loudly.

**No `_KNOWN_BAD_FACTS` entries were added for them.** Covering the five periods would take about
twenty entries, because each is reported under two tags at two period lengths, and the list would
grow with every re-filing. A general rule is the better answer and it now has a stated basis.

**`EXE 2019-02-01` stays rescaled.** It is almost certainly the eleventh contradicted row, but it
carries no EPS triple to prove it, and the no-evidence default is to rescale. Consistency with
the stated default beats a one-off exception.

**`calculate_ttm` still rolls over four available rows rather than four calendar quarters** —
carried forward from the tag investigation through the split task and untouched again here.

**The sweep's own thresholds are unaudited.** `_GATE_LOG_GAP = 1.5` and `_MATCH_TOLERANCE = 0.5`
decide which values it looks at and which factors it will accept. They were not tuned in this
task, and with the gate in place a loose threshold now costs a rejected proposal rather than a
corrupted value — the risk it carried has been shifted, not measured.

---

## Files changed

| file | change |
|---|---|
| `parsers/parse_edgar.py` | new `_facts_by_filing`, `_scale_evidence`, `_income_for_period`, `_corroborated_scale_correction`; `build_dataframe` now gates the sweep's proposals on the filings instead of applying them unconditionally. `_normalize_scale_outliers` itself is unchanged. |
