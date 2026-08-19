# Per-category tag work — the 112 `standard` candidates

First category from `next_500_candidates.md` §5.2: the 112 tickers proposed as `standard`,
$6.23bn to $191bn. Measured 2026-08-19 from a cold EDGAR fetch, then entirely from the warm
cache with no further network access.

**Control.** Before anything was changed, the pipeline's own `build_dataframe` +
`check_data_quality` over the 500 cached universe tickers reproduces **733 flags**, matching
`full_refresh_report.md` exactly. Everything below rests on that reproduction. *(The brief
quotes 737; the run report says 733, and 733 is what reproduces.)*

---

## 0. What came out

| | |
|---|---|
| candidates surveyed | **112**, all resolved, no `CIK_OVERRIDES` needed |
| flags raised | **274** across 107 tickers — **2.45 per ticker** vs the universe's **1.47** |
| class **A** (tag gap, fixable) | **21 of 274 = 7.7%** |
| class **B** + **C** (not fixable by any tag) | **253 = 92.3%** |
| global `CONCEPT_CANDIDATES` additions made | **zero** — every candidate tag fails on the existing 500 |
| per-ticker overrides applied | **7**, across 5 tickers |
| existing 500 after the change | **0 appeared, 0 changed, 0 disappeared**; 733 → 733 flags |
| anchor invariant | **0** series moved backward (holds the 0/0 record, now twelve tasks) |

Three results carry the task.

**The candidates look 67% worse and are not.** 2.45 flags per ticker against 1.47 is a real
difference, but **92.3% of it is class B or C** — a software company with no dividend, no
buyback and no debt. The single largest group, `DividendsPerShare` at 89 flags, is **0%
actionable**: 80 of those 89 filers carry no dividend-family tag of any kind, because they have
never declared a dividend.

**Not one tag survived as a global addition.** Every class-A fix was checked against the
existing 500 before being proposed, and all ten candidate tags failed. `LineOfCredit` is the
clearest: 173 existing tickers carry it, and its median ratio to their current long-term debt is
**0.002**. Adding it globally would have injected 756 values two-and-a-half orders of magnitude
too small. All seven applied fixes are per-ticker.

**One value was deleted, and the deletion is correct.** GWRE's `LongTermDebt` at 2022-07-31
disappears. It is not a regression: Guidewire adopted ASU 2020-06 on the first day of FY2023 and
the carrying amount of its convertible notes steps from $358.2m to $395.5m **in one day**.
Section 6.2 shows the accretion series that proves it.

---

## 1. What was added to `config.py`

Everything is inside `# >>> PROVISIONAL … # <<< END PROVISIONAL` markers, in two blocks. Both
are one contiguous `git diff` hunk.

### 1.1 Scaffolding — remove if the candidates are not admitted

**Block 1, `TICKER_PROFILES`: the 112 tickers as `standard`.** Nothing can be fetched or parsed
for a ticker that is not in this dict, so the investigation cannot start without it. This is
**not an admission decision** — 67 of the 112 still carry an open profile question. Removing the
block restores the 500-ticker universe exactly.

**No `CIK_OVERRIDES` were needed.** All 112 resolve against today's `company_tickers.json`, to
exactly the CIK the survey recorded — 0 absent, 0 mismatched. Worth stating because the AEP
precedent makes the opposite a live possibility.

### 1.2 Proposed permanent — the seven class-A fixes

**Block 2, `TICKER_CONCEPT_OVERRIDES`.** These are proposed to keep, and they are inside the
provisional markers only because they are keyed to tickers that are not yet admitted. If the
candidates are admitted, the markers come off and the entries stay. If they are not, the whole
block goes.

| ticker | concept | tag added | evidence |
|---|---|---|---|
| GWRE | `NetIncomeLoss` | `ProfitLoss` | identical on **8/8** overlapping quarters; carries no NCI tag at all |
| MORN | `NetIncomeLoss` | `ProfitLoss` | identical on **30/30** |
| SMTC | `NetIncomeLoss` | `ProfitLoss` | identical on **33/33** |
| GWRE | `LongTermDebt` | `SeniorNotes` | identical on **5/5**; 48–56% of total liabilities, and the convertible notes are Guidewire's only borrowing |
| MORN | `LongTermDebt` | `LineOfCredit` | identical on **12/12**; 36–45% of total liabilities |
| RGTI | `LongTermDebt` | `DebtInstrumentCarryingAmount` | identical on **4/4**, *and* exact against the filer's own maturity schedule on 4/4 |
| APPF | `LongTermDebt` | `DebtInstrumentCarryingAmount` | matches the filer's own maturity schedule within **2.0%** on 3/3 |

The `ProfitLoss` entries follow the existing `KEYS` precedent exactly. The `LongTermDebt`
entries restate the full `sources` list with one tag appended last, so `priority_merge` reaches
the new tag only where every existing source is empty.

---

## 2. The Step 1 survey

112 tickers, 224 EDGAR requests (companyfacts + submissions), 0 errors. No Yahoo requests were
made: the survey had already spent ~9,200 there, and nothing in this task needs a price.

### 2.1 Flag rate against the existing baseline

| | existing 500 | candidates 112 |
|---|---:|---:|
| flags | 733 | **274** |
| tickers flagged | 366 (73%) | **107 (96%)** |
| flags per ticker | **1.47** | **2.45** |

**1.67× the maintenance load per ticker**, on the face of it. Section 3 is what that number
actually costs.

### 2.2 By concept — where the excess sits

| concept | cand | exist | cand % | exist % | Δpp |
|---|---:|---:|---:|---:|---:|
| `DividendsPerShare` | 89 | 151 | 79.5 | 30.2 | **+49.3** |
| `LongTermDebt` | 44 | 48 | 39.3 | 9.6 | **+29.7** |
| `StockRepurchased` | 54 | 122 | 48.2 | 24.4 | **+23.8** |
| `Goodwill` | 21 | 53 | 18.8 | 10.6 | +8.2 |
| `OperatingIncomeLoss` | 13 | 36 | 11.6 | 7.2 | +4.4 |
| `Capex` | 8 | 18 | 7.1 | 3.6 | +3.5 |
| `StockIssued` | 23 | 123 | 20.5 | 24.6 | −4.1 |
| `ShareBasedCompensation` | 1 | 67 | 0.9 | 13.4 | **−12.5** |

Two of these are worth reading rather than counting.

`ShareBasedCompensation` is **twelve points better** in the candidates than in the universe.
That is the July fix working exactly where it should: the tag appended then
(`AdjustmentsToAdditionalPaidInCapital…RequisiteServicePeriodRecognitionValue`) is how software
companies tag SBC, and SBC is the one line this cohort never omits.

`DividendsPerShare` and `StockRepurchased` are together **143 of the 274 flags** and, as
section 3 shows, **zero of them are actionable**.

### 2.3 The three sub-clusters

**SIC 7372, prepackaged software — 36 candidates.** Marginally worse than the rest of the
category and for a structural reason, not a tagging one:

| | 7372 (36) | the other 76 |
|---|---:|---:|
| flags per ticker | 2.75 | 2.30 |
| us-gaap facts, median | 9,946 | 17,372 |
| parsed rows, median | 436 | 757 |
| **history, median** | **8.9 y** | **14.4 y** |

Their five commonest flags are `DividendsPerShare` (33 of 36), `StockRepurchased` (23),
`LongTermDebt` (19), `StockIssued` (5), `NetIncomeLoss` (2). The first three are the profile of
a company that pays no dividend, has not started buying back stock, and funds itself with
equity. This cluster is not harder to extract — it has less to extract.

**Two or fewer 10-Ks — 11 candidates.** Short history is not a defect, but it bounds what any
metric can say:

| ticker | market cap | history | span | flags |
|---|---:|---|---:|---:|
| SHOP | $191.00bn | 2012-12 → 2026-06 | 13.5 y | **13** |
| CRWV | $58.46bn | 2022-12 → 2026-06 | 3.5 y | 1 |
| ALAB | $55.54bn | 2021-12 → 2026-06 | 4.5 y | 4 |
| CLS | $42.93bn | 2021-12 → 2026-06 | 4.5 y | 1 |
| TEAM | $40.08bn | 2020-06 → 2026-06 | 6.0 y | 1 |
| RBRK | $20.79bn | 2022-01 → 2026-04 | 4.2 y | 2 |
| FIG | $13.32bn | 2022-12 → 2026-06 | 3.5 y | 3 |
| SAIL | $10.54bn | 2023-01 → 2026-04 | 3.2 y | 3 |
| TTAN | $8.43bn | 2022-01 → 2026-04 | 4.2 y | 3 |
| NAVN | $7.30bn | 2023-01 → 2026-04 | 3.2 y | **12** |
| HNGE | $7.09bn | 2022-12 → 2026-06 | 3.5 y | 3 |

Median history **4.2 years against 13.5** for the rest, and **9 of 11 have under five years**.
Every 5-year rolling mean for those nine is computed on a window that is barely longer than the
window itself, and a 15-year comparison chart shows them as a stub.

**SHOP is the outlier and not for the reason the group implies.** It has 13.5 years of
*price* history but only 179 parsed rows and 13 flags — it appears in the class-B list for
**twelve separate concepts**, with a thirteenth flag that is class C. Shopify filed 40-F under IFRS until recently; its us-gaap facts
begin only at the conversion. This is the "converted foreign filer" category the survey flagged
(§6.2 there), showing up as a data-density problem rather than a scope one. **The largest
company in this category has the thinnest us-gaap record in it.**

**The >2× market-cap disagreements — only 2 of the survey's 29 are in this category**, and the
defect does **not** reach the fundamentals:

| ticker | diluted shares, latest two quarters | verdict |
|---|---|---|
| OWL | 681,072,472 → 688,509,841 | whole shares, no scaling defect |
| MBLY | 817,000,000 → 818,000,000 | whole shares, no scaling defect |

Both disagreements were **dual-class understatement in the survey's own stage-1 estimator**,
which read one share class out of the XBRL frames API. The pipeline does not use frames for
share counts, so it never saw the error. Checked across all 112: **every one has a parsed
`SharesOutstanding` series, zero `SharesOutstanding` flags, and implied prices from $5.27 to
$1,787** — no value anywhere near the 1,000× signature that TBLA, RPAY and MODD show. The
directional scale detector was not needed and did not fire.

---

## 3. The A/B/C breakdown

| concept | **A** | **B** | **C** | total | actionable |
|---|---:|---:|---:|---:|---:|
| `DividendsPerShare` | 0 | 9 | 80 | 89 | **0%** |
| `StockRepurchased` | 0 | 46 | 8 | 54 | **0%** |
| `LongTermDebt` | 11 | 16 | 17 | 44 | 25% |
| `StockIssued` | 3 | 20 | 0 | 23 | 13% |
| `Goodwill` | 0 | 14 | 7 | 21 | **0%** |
| `OperatingIncomeLoss` | 0 | 6 | 7 | 13 | **0%** |
| `Capex` | 2 | 3 | 3 | 8 | 25% |
| `NetIncomeLoss` | 3 | 1 | 0 | 4 | 75% |
| `PretaxIncome` | 0 | 3 | 1 | 4 | 0% |
| `DepreciationAndAmortization` | 0 | 3 | 1 | 4 | 0% |
| `IncomeTaxExpense` | 0 | 2 | 1 | 3 | 0% |
| `CashAndEquivalents` | 2 | 0 | 0 | 2 | 100%\* |
| `OperatingCashFlow` | 0 | 2 | 0 | 2 | 0% |
| `Revenue` | 0 | 2 | 0 | 2 | 0% |
| `ShareBasedCompensation` | 0 | 1 | 0 | 1 | 0% |
| **total** | **21** | **128** | **125** | **274** | **7.7%** |

\* both `CashAndEquivalents` cases were rejected on the scope test — see 4.2. Actionable by
*mechanism* is not actionable in *fact*.

**`DividendsPerShare`, 89 flags, 0% actionable, and 80 of them class C.** There is not one
unqueried dividend-family tag anywhere in the 112. This is the same shape as the
`StockRepurchased` finding in `tag_investigation_stock_sbc_report.md` — 0 of 126 there, 0 of 54
here — and it generalises the lesson: when a whole cohort is flagged on one concept, the first
hypothesis should be that the cohort does not have the item.

**`StockRepurchased` reconfirms 0% across a second, disjoint population.** The unqueried tags
these filers carry are `StockRepurchaseProgramRemainingAuthorizedRepurchaseAmount1` (23
tickers), `TreasuryStockAcquiredAverageCostPerShare` (16), `TreasuryStockCommonShares` (15) and
`StockRepurchasedAndRetiredDuringPeriodShares` (13) — an authorisation, a per-share price and
two share counts. Not one is a dollar flow of common-stock repurchases.

### 3.1 Class C — no accepted-family tag exists at all (125)

- **`DividendsPerShare` (80):** SHOP, SNOW, NET, ALAB, CRDO, CLS, TEAM, P, MDB, TWLO, ZM, ZS, CPNG, RBLX, MTSI, OKTA, IOT, SITM, FN, RBRK, U, IONQ, LSCC, NTNX, FLUT, DOCN, NXT, TTMI, SMTC, CACI, GWRE, W, AUR, DT, FIG, AAOI, PINS, SANM, MANH, DOCU, VIAV, CART, ARW, RMBS, FORM, HUBS, SAIL, COMP, CHWY, APLD, PCOR, SNAP, PL, ESTC, HQY, QRVO, TTAN, PATH, SNEX, ALGM, PCTY, MBLY, MXL, Z, S, LNWO, SLAB, PLXS, NAVN, DBX, ZETA, ETSY, HNGE, APPF, GTLB, LYFT, WEX, QLYS, AXTI, RGTI
- **`LongTermDebt` (17):** ALAB, CRDO, IOT, TW, IONQ, LOGI, AUR, FIG, FROG, MANH, CART, CHWY, PATH, MBLY, HNGE, GTLB, QLYS
- **`StockRepurchased` (8):** SITM, TPG, AAOI, COMP, PL, TTAN, NAVN, RGTI
- **`Goodwill` (7):** UI, IOT, AAOI, TRNO, PLXS, ACT, AXTI
- **`OperatingIncomeLoss` (7):** LPLA, TPG, CG, EQH, EVR, TRNO, ACT
- **`Capex` (3):** TPG, EQH, ACT
- **`DepreciationAndAmortization` (1):** ACT · **`IncomeTaxExpense` (1):** TRNO · **`PretaxIncome` (1):** TRNO

### 3.2 Class B — the family exists but yields nothing new (128)

- **`StockRepurchased` (46):** SHOP, MELI, CRWV, ALAB, CRDO, TWLO, ZS, RBLX, OKTA, IOT, FN, RBRK, U, IONQ, SSNC, JLL, AMKR, RBA, NXT, TTMI, GWRE, W, AUR, FIG, FROG, DOCU, HUBS, CHWY, APLD, PCOR, SNAP, ESTC, HQY, PATH, ALGM, PCTY, ESE, MBLY, MXL, Z, S, HNGE, APPF, GTLB, LYFT, AXTI
- **`StockIssued` (20):** SHOP, MELI, FN, TPG, OWL, JLL, AMKR, NXT, TTMI, LOGI, EQH, EVR, MANH, CHWY, HLI, AVT, ESE, MBLY, LNWO, ACT
- **`LongTermDebt` (16):** SHOP, SNOW, ZM, SITM, TOST, NXT, DT, PINS, SAIL, COMP, APLD, PL, TTAN, PCTY, S, NAVN
- **`Goodwill` (14):** ALAB, CRDO, CPNG, SITM, FN, AUR, EQH, PINS, SANM, CHWY, IDCC, APLD, NAVN, RGTI
- **`DividendsPerShare` (9):** MELI, TOST, JLL, AMKR, RBA, LOGI, FROG, PAYC, MTCH
- **`OperatingIncomeLoss` (6):** SHOP, OWL, AMG, SNEX, ESE, NAVN
- **`Capex` (3):** SHOP, JLL, NAVN · **`DepreciationAndAmortization` (3):** SHOP, EQH, NAVN · **`PretaxIncome` (3):** SHOP, TPG, NAVN
- **`IncomeTaxExpense` (2):** SHOP, NAVN · **`OperatingCashFlow` (2):** SHOP, NAVN · **`Revenue` (2):** SHOP, NAVN
- **`NetIncomeLoss` (1):** SHOP · **`ShareBasedCompensation` (1):** SHOP

These lists are the permanent record. Without them the next investigation re-derives 253
non-findings.

---

## 4. Every change, and every rejection

### 4.1 Why nothing was added globally

Ten tags could have closed a class-A gap. Each was measured across the **existing 500** before
being considered — how many carry it, how many values a global addition would inject at ends the
current tags leave empty, and how often it agrees where both are present:

| concept | candidate tag | existing holders | values it would inject | identical where co-reported | median ratio | verdict |
|---|---|---:|---:|---:|---:|---|
| `LongTermDebt` | `LineOfCredit` | 173 | 756 | **2.3%** | **0.002** | reject |
| `LongTermDebt` | `LongTermLineOfCredit` | 33 | 197 | 5.0% | 0.121 | reject |
| `LongTermDebt` | `SeniorNotes` | 85 | 497 | 11.3% | 0.781 | reject |
| `LongTermDebt` | `NotesPayable` | 58 | 752 | 36.3% | 1.000 | reject |
| `LongTermDebt` | `DebtInstrumentCarryingAmount` | 264 | 1,266 | 53.7% | 1.008 | reject |
| `NetIncomeLoss` | `ProfitLoss` | 406 | 733 | 49.0% | 1.005 | reject |
| `Capex` | `PaymentsToAcquireOtherPropertyPlantAndEquipment` | 31 | 378 | 31.0% | 1.000 | reject |
| `Capex` | `PaymentsToAcquireIntangibleAssets` | 108 | 156 | **0.1%** | **0.033** | reject |
| `StockIssued` | `ProceedsFromIssuanceInitialPublicOffering` | 52 | 30 | 6.8% | 0.000 | reject |
| `CashAndEquivalents` | `CashCash…RestrictedCash…` | 478 | 2,122 | 58.2% | 1.003 | reject |

A median ratio near 1.000 is not sufficient — the tail is what does the damage:

```
LineOfCredit          AEP   2020-03-31   current 27,892,700,000   tag      30,500,000   x0.001
DebtInstrumentCarry…  BALL  2025-12-31   current      2,000,000   tag   7,052,000,000   x3,526
ProfitLoss            ACGL  2020-03-31   current    144,117,000   tag     -88,674,000   SIGN FLIP
PaymentsToAcquireInt… AAPL  2017-12-30   current  2,810,000,000   tag     154,000,000   x0.05
IPO proceeds          COF   2011-09-30   current     10,000,000   tag   3,000,000,000   x300
RestrictedCash        ABNB  2025-06-30   current  7,402,000,000   tag  18,444,000,000   x2.49
```

`DebtInstrumentCarryingAmount` is the instructive one: 53.7% identical, median ratio 1.008, and
it would still put $7.05bn of debt on Ball Corporation where the pipeline currently has $2m. It
is a **per-instrument footnote tag**. It equals the total exactly when the filer has one
instrument, and is unrelated to it otherwise — which is why it is right for RGTI and APPF and
wrong for 264 existing tickers.

`ProfitLoss` fails for a different reason and a cleaner one: it *includes* noncontrolling
interests where `NetIncomeLoss` excludes them. On ACGL that flips the sign.

**Conclusion: `sum` versus `fallback` never arose.** The question is upstream of it — none of
these tags is safe to place in a shared list at all, in either mode. All seven fixes are
per-ticker `TICKER_CONCEPT_OVERRIDES`. No `_KNOWN_BAD_FACTS` entry was needed: there is no
single wrong value here, only absent ones.

### 4.2 Rejections, with the evidence

| case | tag | why rejected |
|---|---|---|
| **SITM, NAVN** `CashAndEquivalents` | `CashCash…RestrictedCash…` | Wrong quantity. On NAVN's overlapping quarters it runs **+96.99%, +24.43%, +14.49%, +10.65%** against the current extraction — it includes restricted cash, which cash-and-equivalents excludes by definition. SITM has no plain-cash values at all, which makes it look like a free gain and is the same wrong number. |
| **SNEX** `LongTermDebt` | `LineOfCredit` | A component. **−70.4%, −67.3%, −63.7%** on the three most recent overlaps ($488.8m against $1,648.4m). |
| **MELI** `LongTermDebt` | `LongTermLineOfCredit` | A component, extremely: $1,000,000 against $9,193,000,000 — **−99.99%**. Would have added two historical values at a level unrelated to MELI's actual debt. |
| **FN** `LongTermDebt` | `LineOfCredit` | Fails the independent check: **+49.1%, +71.1%, +71.1%** against the filer's own maturity schedule. |
| **AXTI** `LongTermDebt` | `LongTermLineOfCredit` | Fails the independent check: −18.8%, −18.2%, **−45.6%** against the maturity schedule. It is the noncurrent portion; the schedule includes the current one. |
| **PCOR** `LongTermDebt` | `LineOfCredit` | Every value is **0**. Procore has no borrowings; five zeros do not close a gap. |
| **EVR** `LongTermDebt` | `NotesPayable` | 36 ends, and **no way to verify**: no overlapping quarter, and no maturity schedule tagged. 17–31% of total liabilities is plausible and not evidence. Left as an identified, unapplied class-A fix. |
| **HUBS** `LongTermDebt` | `LineOfCredit` | One end, 2014. Immaterial. |
| **LYFT** `Capex` | `PaymentsToAcquireIntangibleAssets` | One end, value 0, and the wrong quantity — intangibles are not property, plant and equipment. |
| **TRNO** `Capex` | `PaymentsToAcquireOtherPropertyPlantAndEquipment` | 64 ends, the largest single class-A find, **and deliberately not applied** — see §7. |
| **CG, SAIL, PAYC** `StockIssued` | `ProceedsFromIssuanceInitialPublicOffering` | Right quantity, almost no content. 15 ends across three tickers, most of them zero; the one material value (CG 2014-03-31, $449.5m) is a single quarter. SAIL's overlapping quarter shows the existing tags already capture the IPO ($1,251.4m against the IPO tag's $1,259.7m, +0.66% — gross versus net of costs). Not worth a per-ticker entry. |

---

## 5. Which tickers got depth

**Depth — 55 tickers.** The top 40 by market cap (down to $15.08bn) plus all 15 class-A tickers
below that line: APPF, AXTI, EVR, GWRE, HUBS, LYFT, MORN, NAVN, PAYC, PCOR, RGTI, SAIL, SMTC,
SNEX, TRNO. Depth means the raw facts were read, the specific tag identified, the mode decided,
and the value checked against either the filer's own overlapping quarters or its separately
tagged maturity schedule.

**Survey only — 57 tickers.** Ranks 41–112 with no class-A finding. They have the Step 1
measurement (fact counts, period range, which concepts resolve, flags) and the A/B/C class for
every flag, but no raw-fact reading.

**Where the next pass should start:** the survey-only 57, in market-cap order from **NXT
($15.03bn)**, then TTMI ($14.85bn), LOGI ($14.48bn), CACI ($14.35bn). Expect little — the A/B/C pass already ran over all 274 flags, so any class-A case
among them would have shown up. The realistic yield is in re-examining the class-B `LongTermDebt`
group (16 tickers) where the family exists and produces nothing new, which usually means an
annual-only disclosure cadence rather than a tag gap.

---

## 6. Non-regression

Both states were built from the same warm cache in the same process shape, with **no price
capture involved** — none of the layers compared needs one. `get_price_history` is not
bit-reproducible (`product_cleanup_report.md`), which is exactly why the comparison was scoped
to the layers that are: base facts, `_TTM`, and `metrics_long`.

### 6.1 The diff

| layer | population | appeared | changed | disappeared |
|---|---|---:|---:|---:|
| facts (incl. `_TTM`) | **existing 500** | **0** | **0** | **0** |
| facts (incl. `_TTM`) | candidates 112 | 534 | 9 | 1 |
| `metrics_long` | **existing 500** | **0** | **0** | **0** |
| `metrics_long` | candidates 112 | 591 | 18 | 2 |

Rows gained, by ticker: GWRE 231, MORN 163, SMTC 136, APPF 2, RGTI 2.

**The existing 500 are untouched, and by construction they had to be**: a
`TICKER_CONCEPT_OVERRIDES` entry is looked up by ticker in `get_concept_candidates`, and all five
touched tickers are candidates. The measurement confirms the argument rather than replacing it —
which is the point, since the argument would not have survived a global `CONCEPT_CANDIDATES`
addition, and that is what §4.1 stopped.

**Every one of the 27 "changed" values is `NaN → a number`** — 9 facts (SMTC's
`NetIncomeLoss_TTM`, `EPS_TTM_CALC` and `FFO_TTM` for three 2018 quarters, now that the TTM
window has four quarters) and 18 metrics (SMTC `income_yoy_growth`, `roe`, `rotce`,
`ffo_margin`; MORN `buyback_distortion_flag` 0 → 1 for two quarters, which is the flag doing its
job on a newly populated series). No previously-populated value moved.

### 6.2 The one deletion, justified

`GWRE LongTermDebt 2022-07-31 = $358,216,000` disappears, taking `debt_to_equity` and
`net_debt_to_ebitda` at that date with it. The cause is `merge_duplicate_period_ends`, whose
documented rule is that within a seven-day gap **the later end survives**. Adding `SeniorNotes`
brings in a value at **2022-08-01**, one day later, and the two collapse.

They are not the same measurement, and keeping the later one is right:

```
GWRE SeniorNotes, carrying amount and sequential change
   2022-01-31    350,921,000    +3,572,000
   2022-04-30    354,544,000    +3,623,000
   2022-07-31    358,216,000    +3,672,000     <- fiscal year end, pre-adoption
   2022-08-01    395,469,000   +37,253,000     <- first day of FY2023
   2022-10-31    395,891,000      +422,000
   2023-01-31    396,316,000      +425,000
   2023-04-30    396,743,000      +427,000
```

Four years of accretion at $2.9m–$3.7m a quarter, **$37.3m in a single day**, then $422k–$432k a
quarter. That is the signature of adopting **ASU 2020-06** on the first day of FY2023: the
equity-conversion component is reclassified into debt, the discount disappears, and subsequent
accretion collapses to issuance-cost amortisation alone. `CumulativeEffectOfNewAccountingPrincipleInPeriodOfAdoption`
is present in GWRE's facts. Keeping 2022-08-01 gives 27 points on one continuous accounting
basis; keeping 2022-07-31 would give 28 with a $37m discontinuity in the middle.

### 6.3 Invariants and flags

**Anchor invariant: 0 series moved backward**, across all 612 tickers and both populations. Now
0/0 for twelve tasks.

| | before | after |
|---|---:|---:|
| existing 500 flags | 733 | **733** |
| candidate flags | 274 | **269** |

Cleared: GWRE `NetIncomeLoss`, MORN `NetIncomeLoss`, SMTC `NetIncomeLoss`, MORN `LongTermDebt`,
RGTI `LongTermDebt`. **Zero new flags in either population.**

GWRE `LongTermDebt` and APPF `LongTermDebt` are **not** cleared despite the fix: GWRE goes from
9 ends to 27 and APPF gains 2, both still under the 50% threshold. The data improved; the flag
is measuring coverage, and coverage is still thin. Reporting the fix as "5 flags cleared" rather
than "7 fixes applied" would be the misleading framing.

**Mean-line effect: not measured, and it cannot be non-zero for the existing universe.** Every
running-series line in the brief's table (TTM ~25%, rolling-window 11–15%, duplicate-ends 2–5%,
alignment 0–3.7%, FFO gains 0.6–1.5%, annual-gate 0–0.07%) is a function of the facts, and the
existing 500's facts are byte-identical before and after. For the candidates the question is not
yet meaningful — they have no mean lines until they are admitted.

### 6.4 Independent plausibility check

Not against the pipeline's own arithmetic. `LongTermDebtMaturitiesRepaymentsOfPrincipal*` is a
separate disclosure of the same obligation, tagged from the debt footnote:

| ticker | tag value | filer's own maturity schedule | difference |
|---|---:|---:|---|
| RGTI 2021-12-31 | 27,000,000 | 27,000,000 | **0.0%** |
| RGTI 2022-03-31 | 32,000,000 | 32,000,000 | **0.0%** |
| RGTI 2022-06-30 | 32,000,000 | 32,000,000 | **0.0%** |
| RGTI 2022-09-30 | 32,000,000 | 32,000,000 | **0.0%** |
| APPF 2019-12-31 | 48,750,000 | 48,750,000 | **0.0%** |
| APPF 2020-03-31 | 48,438,000 | 47,500,000 | +2.0% |
| APPF 2020-06-30 | 48,125,000 | 47,500,000 | +1.3% |

APPF's small positive difference is the expected direction: the schedule is principal due, the
tag is carrying amount including accrued items. The same check is what rejected FN and AXTI.

---

## 7. Tickers with an open profile question

67 of the 112. Extraction is profile-independent and was done for all of them; **no visibility
decision was made for any**. Two findings are recorded and left open:

**TRNO — the largest single class-A find, deliberately not applied.** Terreno Realty is proposed
`standard` from SIC 6500, and it is an industrial REIT. `PaymentsToAcquireOtherPropertyPlantAndEquipment`
would add **64 quarters** of `Capex` where the pipeline currently has none. But whether that is
Terreno's capex depends entirely on which profile it lands on: for a `standard` company, buying
property is capex; for a `reit`, property acquisition is portfolio growth and maintenance capex
is a different, smaller line. TRNO also carries `PaymentsToAcquireBuildings`, which is the
acquisition line. **Applying either tag is a profile decision wearing a tag decision's clothes**,
so neither was applied. TRNO is also class C on `Goodwill`, `IncomeTaxExpense`, `PretaxIncome`
and `OperatingIncomeLoss` — four concepts a REIT does not report the way a `standard` company
does, which is itself evidence about the profile.

**The `6282` cluster behaves like a group.** TPG, OWL, CG, EVR, AMG, HLI, MORN and VCTR are the
survey's open `standard`/`alt_asset_manager` question. TPG, CG, EQH and EVR are class C on
`OperatingIncomeLoss`, and TPG is class C on `Capex` and `StockRepurchased` too — asset managers
do not present an operating-income subtotal. Whichever profile they get needs
`PROFILE_EXCLUDED_CONCEPTS` treatment for `OperatingIncomeLoss`; on `standard` today they would
each show an empty panel. Recorded, not decided.

---

## 8. Deliberately not done

**No global tag additions**, for the reason in §4.1. This is the main deliverable and it is a
negative one.

**EVR `NotesPayable` not applied.** 36 ends is the second-largest class-A find and I could not
verify it. Two ways forward, neither in scope: read the 10-K debt footnote directly, or wait
until an overlapping quarter appears.

**`DividendsPerShare` threshold not touched.** 89 of 112 candidates are flagged on a concept
where 80 of them have no tag at all. The flag is arithmetically correct and informationally
empty, and the same is true of 151 existing tickers. Making `DividendsPerShare` conditional —
suppressed when the filer has never carried a dividend tag — would remove ~230 flags across both
populations and is a `quality.py` change, not a tag change.

**The `StockRepurchased` share-count tags were not pursued.** `StockRepurchasedAndRetiredDuringPeriodShares`
and `TreasuryStockAcquiredAverageCostPerShare` multiply out to a dollar value, and 13 and 16
candidates respectively carry them. That is a derived concept, not a tag gap, and inventing one
inside a tag investigation is how a plausible wrong number gets in.

**No `PROFILE_HIDDEN` or `PROFILE_CONCEPT_OVERRIDES` changes**, per the brief.

**SHOP's IFRS-era gap was not addressed.** Its us-gaap facts begin at the 40-F conversion, which
is why it is class B on twelve concepts. Reaching further back means reading IFRS facts, a
fetch/parse-layer change of the same shape as the XOM dual-CIK merge, and equally out of scope.

**The provisional block was left in place** so the measurement can be reproduced. It is one
contiguous hunk in each of the two config sections and removing both restores the 500-ticker
universe exactly.
