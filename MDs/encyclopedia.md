# Metric Reference

What each number means, how to read it, and where it lies to you.

This is the interpretation guide. It assumes no finance background. If you want to know how the numbers are computed, see the module docs; if you want to know what they *tell* you, read on.

---

## Before anything else: two questions, not one

Every metric in this tool answers one of two questions, and confusing them is the most common mistake in stock analysis.

**Is this a good business?** → the *fundamentals*. Revenue growth, margins, returns, leverage. These describe the company itself and have nothing to do with the share price. A company can be excellent and still be a terrible investment.

**Is this stock expensive?** → the *valuation multiples*. P/E, P/B, EV/EBITDA and friends. These describe what the market is charging you for a claim on that business. A mediocre company at a cheap enough price can be a fine investment.

You need both. A great business at an absurd price loses money. A cheap price on a dying business loses money faster.

---

# Part 1: Fundamentals

## Revenue growth (YoY)

**What it is:** How much larger this year's sales are than last year's. Measured on a trailing-twelve-month basis, comparing to the same point one year ago.

**Why it matters:** Revenue is the top line — everything else is derived from it. It is also the hardest number to manipulate. Profit can be massaged through accounting choices; sales are sales.

**How to read it:**
- Consistent positive growth is the baseline expectation for a healthy company
- **Acceleration** is more interesting than the absolute level. A company going 5% → 8% → 12% is telling a different story than one going 20% → 15% → 10%, even though the second has higher numbers
- Mature companies (Walmart, Coca-Cola) growing 3–5% is normal and fine
- Negative growth is a red flag unless there is a clear one-off explanation

**Where it lies:** Growth can be bought. A company that acquires competitors shows revenue growth without necessarily creating any value. Check whether margins are holding — if revenue grows while margins collapse, the growth may be purchased with discounts.

---

## Earnings growth (YoY)

**What it is:** The same comparison, applied to net income (profit after everything).

**Why it matters:** Ultimately, a share of stock is a claim on future profits. If profits aren't growing, the case for a rising share price rests entirely on the market being willing to pay a higher multiple — which is a bet on sentiment, not on the business.

**How to read it:**
- Should broadly track revenue growth over time
- **Earnings growing faster than revenue** means margins are expanding — the company is getting more efficient or gaining pricing power. This is one of the most reliable signals of a strengthening business
- **Earnings growing slower than revenue** means margins are shrinking — costs are rising faster than sales, or the company is discounting to win business

**Where it lies:** Profit is the most manipulable number in the accounts. It can be inflated by one-off asset sales, deflated by write-offs, or shifted between periods through accounting choices. A single spike or collapse usually reflects an event, not a trend.

The chart uses a symmetric log scale, because a single outlier (NVIDIA's earnings grew ~800% in one year) would otherwise flatten everything else into a straight line.

---

## Operating margin

**What it is:** Operating profit divided by revenue. Of every dollar of sales, how many cents survive the cost of running the business — before interest and taxes.

**Why it matters:** This is the purest available measure of **pricing power**. A company that can raise prices without losing customers has high margins. A company competing on price does not.

**How to read it:**
- The absolute level is only meaningful *within an industry*. Software companies run at 30–50%. Supermarkets run at 3–6% and that is not a problem — they make it back on volume. Comparing Walmart's 4% to Microsoft's 46% tells you nothing except that they are different businesses
- **The trend is what matters.** Rising margins over years is one of the strongest signals in fundamental analysis. It means the company is becoming harder to compete with
- Falling margins mean the opposite: competition is biting, or costs are outrunning prices

**Where it lies:** Margins can be flattered short-term by cutting spending that matters — R&D, marketing, maintenance. That looks like efficiency for two years and like decay afterwards.

---

## Free cash flow margin

**What it is:** Free cash flow (operating cash flow minus capital expenditure) divided by revenue. Of every dollar of sales, how many cents end up as **actual cash** the company can do something with.

**Why it matters:** Profit is an opinion; cash is a fact. Accounting profit involves judgment calls about when to recognize revenue and how to spread costs. Cash either arrived in the bank or it didn't.

Free cash flow is what pays dividends, funds buybacks, retires debt, and finances growth without dilution. It is the money that is genuinely *free*.

**How to read it:**
- Should be broadly in line with net margin. If a company reports strong profits but weak cash flow **year after year**, something is wrong — profits are being booked that don't turn into money
- Capital-intensive businesses (manufacturing, telecoms) have structurally lower FCF margins because they must constantly reinvest. That is not a flaw, it's the business model
- Software and asset-light businesses often have FCF margins above net margin, because they barely need capex

**Where it lies:** FCF can be temporarily boosted by cutting capex — which is borrowing from the future. A company that stops maintaining its assets shows great cash flow right up until things break.

---

## Return on equity (ROE)

**What it is:** Net income divided by shareholders' equity. For every dollar of shareholder capital in the business, how much profit does it generate?

**Why it matters:** This is the closest thing to a scorecard for management. Two companies can earn the same profit; the one that does it with less capital is the better business.

**How to read it:**
- 15–20% is good. Above 20% sustained is excellent
- Consistently high ROE over many years suggests a durable competitive advantage — something protecting the company from competitors bidding the returns away
- Negative ROE means a loss-making quarter. This is real information, not a data error

**Where it lies badly — read this part:**

ROE has a denominator problem. Equity shrinks when a company buys back its own shares. Buy back enough stock, and ROE goes up **without the business improving at all**.

Apple's ROE in this tool reads **150–200%**. That is not a data bug and it does not mean Apple is five times better than Microsoft. It means Apple has bought back so much stock that its equity base is small relative to its earnings. The number is arithmetically correct and analytically almost meaningless.

Treat extreme ROE (above ~50%) as a signal to look at *why*, not as a sign of quality. ROIC (return on invested capital) is the better metric here, and this tool does not compute it.

---

## Debt / equity

**What it is:** Total debt divided by shareholders' equity. How much of the company is financed by borrowing versus by owners.

**Why it matters:** Debt amplifies. In good years it magnifies returns; in bad years it magnifies losses, and past a point it kills the company. A business with no debt cannot go bankrupt.

**How to read it:**
- Below 1.0: conservative
- 1.0–2.0: normal for a stable, cash-generative company
- Above 2.0: leveraged; fine if cash flows are predictable, dangerous if they are not
- The **trend** matters more than the level: rising leverage over years is a risk that compounds quietly

**Where it lies:** Same denominator problem as ROE. Buybacks shrink equity, which mechanically raises debt/equity even if no new debt was taken on. Apple's ratio peaked above 2.0 in 2022 largely for this reason.

Also: this metric is **meaningless for banks**. Debt is a bank's raw material, not a burden. A bank with low debt/equity isn't safe, it's just small.

---

## Net debt / EBITDA

**What it is:** Debt minus cash, divided by EBITDA (earnings before interest, taxes, depreciation and amortization — a rough proxy for cash-generating power).

Read it as: **"how many years of earnings would it take to pay off all the debt?"**

**Why it matters:** Debt/equity tells you how leveraged a company is relative to its capital. This tells you how leveraged it is relative to its *ability to pay*. That is usually the more urgent question.

**How to read it:**
- **Negative** means the company holds more cash than debt. It could pay off everything tomorrow. NVIDIA is in this position
- Below 1.0: very comfortable
- 1.0–3.0: normal
- Above 3.0: watch it. Above 4–5, the debt starts driving decisions
- Lenders and rating agencies watch this number closely

**Where it lies:** EBITDA ignores the real costs of interest, taxes, and the eventual need to replace worn-out assets. It flatters capital-intensive businesses. Charlie Munger called it "bullshit earnings" for exactly this reason. Useful as a comparison tool, dangerous as a measure of actual profit.

---

## Payout ratio

**What it is:** Dividends per share divided by earnings per share. What fraction of profits is handed to shareholders as cash.

**Why it matters:** It tells you what the company thinks of its own opportunities. A firm paying out 80% is saying it has nothing better to do with the money. A firm paying out 0% is saying it can reinvest at a good return — and had better be right.

**How to read it:**
- 0%: growth company, reinvesting everything (NVIDIA, historically Amazon)
- 30–50%: balanced — rewarding shareholders while funding growth
- Above 70%: little room left. Any earnings dip forces a choice between cutting the dividend and borrowing to pay it
- **Above 100%: paying out more than it earns.** Funded from reserves or debt. Not sustainable indefinitely

**Where it lies:** A rising payout ratio can mean the dividend went up (good) or that earnings went down (bad). The spike matters less than which of the two caused it. Check earnings growth alongside it.

---

## Rule of 40

**What it is:** Revenue growth (%) plus free cash flow margin (%). If the sum exceeds 40, the company passes.

**Why it matters:** It captures the central trade-off in a growing business: **you can grow fast, or you can be profitable, but growing fast while profitable is rare and valuable.** A company at 60% growth and -20% margin scores 40. So does one at 10% growth and 30% margin. Both are considered healthy — they've just chosen different points on the same curve.

**How to read it:**
- Above 40: passing. The business is converting growth into value rather than buying it
- Below 40: either growth is too slow for the margins being sacrificed, or margins are too thin for the growth being achieved

**Where it lies:** It was invented for software companies and is only really meaningful for them. Applying it to a supermarket (Walmart scores ~8) tells you nothing — retailers were never supposed to hit 40. Ignore this metric outside of high-growth, asset-light businesses.

---

# Part 2: Valuation multiples

These describe the **price**, not the business. All are shown over the last five years, with each company's own five-year average drawn as a reference line — because that is the comparison that matters.

**The core insight:** a multiple in isolation is meaningless. "P/E of 30" is not a fact about whether a stock is expensive. "P/E of 30, against a five-year average of 22" is.

---

## P/E — Price to Earnings

**What it is:** Share price divided by earnings per share (trailing twelve months).

Read it as: **"how many years of current profits am I paying for one share?"** A P/E of 25 means you're paying 25 years of current earnings.

**Why it matters:** The most quoted valuation metric in existence, and a reasonable first approximation of how much optimism is priced in.

**How to read it:**
- **Against its own history first.** Is the company trading above or below its five-year average? That is the question this tool is built to answer
- High P/E means the market expects growth. This is not automatically bad — it becomes bad if the growth doesn't materialize
- Low P/E means the market expects trouble. This is not automatically a bargain — it is often correct
- Rough anchors: below 15 is cheap, 15–25 is typical, above 30 prices in significant growth. But these vary enormously by sector and era

**Where it lies:**
- **Undefined when earnings are negative.** A loss-making company has no meaningful P/E. This tool masks those values rather than printing nonsense
- **Cyclical trap:** for cyclical businesses (autos, mining, semiconductors), P/E is *lowest* at the peak of the cycle — when earnings are at their highest and about to fall. A cyclical stock with a low P/E is often the most dangerous kind
- Earnings are an accounting figure. See P/FCF for the cash-based version

---

## Historical average P/E (5-year)

**What it is:** The average P/E over the last twenty quarters, drawn as a line on the P/E chart.

**Why it matters:** This is the single most useful reference point in the tool. It converts a meaningless number into a comparison.

**How to read it:**
- Current P/E **above** the average: the stock is more expensive than the market has typically been willing to pay for this company
- Current P/E **below** the average: cheaper than usual

**Where it lies:** An average is not a target. If a company has genuinely improved — better margins, faster growth, stronger position — a higher multiple than its history may be entirely justified. And if it has deteriorated, a below-average multiple may still be too high. The average tells you the market has changed its mind; it does not tell you the market is wrong.

---

## P/B — Price to Book

**What it is:** Market capitalization divided by shareholders' equity (book value). What the market pays for a dollar of accounting net worth.

**Why it matters:** A grounding measure. For companies whose value sits in physical, countable assets, book value is a floor of sorts.

**How to read it:**
- Below 1.0: the market values the company at less than its accounting net worth. Either a bargain or a warning that the assets aren't worth what the books say
- **Highly sector-dependent.** For banks and insurers, P/B is a primary valuation tool — their assets *are* financial and reasonably marked. JPM trades around 1.5–2.5, and that range is meaningful
- For tech and asset-light businesses, P/B is close to useless. Apple trades around 45. The value is in the brand, the ecosystem, the installed base — none of which appear on a balance sheet

**Where it lies:** Buybacks shrink book value, which inflates P/B without changing anything real. Intangible-heavy businesses will always look expensive on this measure. Don't use it outside financials and heavy industry.

---

## P/FCF — Price to Free Cash Flow

**What it is:** Market capitalization divided by free cash flow (TTM). The cash-based cousin of P/E.

**Why it matters:** Same question as P/E, but with a number that is much harder to manipulate. If P/E and P/FCF tell different stories, believe P/FCF.

**How to read it:**
- Interpret like P/E: how many years of free cash flow you're paying for
- **A large gap between P/E and P/FCF is a signal.** If P/E looks reasonable but P/FCF is much higher, the company's reported profits aren't converting into cash. That is worth understanding before buying
- The inverse (FCF yield = 1/P/FCF) is often more intuitive: a P/FCF of 20 is a 5% cash yield, comparable to a bond

**Where it lies:** Free cash flow is lumpy. A single large acquisition or a big capex year distorts it. TTM smoothing helps but doesn't eliminate this.

---

## EV/EBITDA — Enterprise Value to EBITDA

**What it is:** Enterprise value (market cap + net debt) divided by EBITDA.

**Why it matters:** P/E ignores debt entirely. Two companies with identical earnings and identical share prices have identical P/Es — even if one is debt-free and the other is mortgaged to the hilt. EV/EBITDA fixes that by pricing the *whole* company, debt included.

This is the metric used in actual acquisitions, because an acquirer inherits the debt along with the business.

**How to read it:**
- Below 10: typically cheap
- 10–15: normal
- Above 20: expensive, priced for growth
- Better than P/E for comparing companies with different capital structures

**Where it lies:** EBITDA adds back depreciation, pretending that worn-out machinery is free. For a software company that's roughly fair. For an airline it is a fantasy — those planes really do need replacing. The more capital-intensive the business, the more EBITDA flatters it.

---

## EV/Sales

**What it is:** Enterprise value divided by revenue.

**Why it matters:** The metric of last resort — it works when nothing else does, because revenue is almost always positive even when earnings and cash flow are not.

**How to read it:**
- The **only** valuation metric that functions for a company that isn't yet profitable. This is why it's ubiquitous for early-stage growth companies
- Meaningful only within an industry. A software company at 10× sales and a supermarket at 0.8× sales may be identically valued in substance — the software company keeps 40 cents of every sales dollar, the supermarket keeps 3

**Where it lies:** It ignores profitability entirely. A company can have wonderful revenue and lose money on every sale. EV/Sales cannot see that. Use it only when the profit-based metrics are unavailable, and always alongside the margin charts.

---

## Dividend yield

**What it is:** Annual dividend per share divided by the share price. The cash return you receive just for holding the stock.

**Why it matters:** It is the only return that doesn't depend on someone else paying more for your shares later.

**How to read it:**
- 0%: growth company. Reinvesting everything. Your return depends entirely on the price rising
- 2–4%: typical for a mature, established business
- **Above 6%: be suspicious.** A very high yield usually means the price has collapsed, not that the dividend is generous. The market may be anticipating a dividend cut
- A **falling** yield over time (visible in the chart) usually means the price rose faster than the dividend — which is a good problem to have

**Where it lies:** Yield is a fraction, and the denominator moves daily. A stock that halves in price doubles its yield without paying a cent more. Always check *why* the yield moved. And check the payout ratio: a high yield backed by a payout ratio above 100% is a dividend cut waiting to happen.

---

## PEG — Price/Earnings to Growth

**What it is:** P/E divided by the earnings growth rate (in percentage points). A P/E of 30 with 30% growth gives a PEG of 1.0.

**Why it matters:** It attempts to answer the obvious objection to P/E: *of course* a fast-growing company should be more expensive. PEG asks whether it is *too* expensive given how fast it's growing.

**How to read it:**
- Below 1.0: growth may be underpriced
- Around 1.0: fairly priced, by the traditional rule of thumb
- Above 2.0: expensive even accounting for growth

**Where it lies — and it lies a lot:**
- **Meaningless when growth is negative or near zero.** JPM shows a PEG of -6.7 in the snapshot. That is not a signal; it's a division by a negative number
- Extremely sensitive to which growth rate you use. Last year's? Next year's estimate? A five-year average? The metric changes entirely depending on the answer
- The rule "PEG below 1 is cheap" has no theoretical foundation. It was a heuristic that became folklore

Treat PEG as a rough sanity check on P/E, never as a decision criterion.

---

## Net Interest Margin (NIM); all following are financial indicators

**What it is:** Net interest income (interest earned minus interest paid) divided by assets. It measures the spread a bank earns on its core business: borrowing cheaply, lending dearly.

**Why it matters:** For a bank, this *is* the engine. A retailer has gross margin; a bank has NIM. It tells you how profitably the institution turns its balance sheet into interest income, independent of one-off gains or fee businesses.

**How to read it:**
- Higher is better, but the range is narrow — most large banks sit between ~1.5% and ~3.5%
- Rising NIM usually means a favourable rate environment (banks reprice loans faster than deposits when rates climb)
- Falling NIM often signals rate compression — JPM's dip toward ~1.4% in 2021/22 is the zero-rate era squeezing the spread

**Where it lies:**
- The denominator here is *total* assets, not strictly *interest-earning* assets. That understates the true margin slightly and makes cross-bank comparison rough — a bank with a large trading book (non-interest-earning assets) will look worse than it is
- NIM says nothing about *volume*. A bank can have a great margin on a shrinking loan book. Read it alongside asset and revenue growth
- It ignores credit risk entirely. A high NIM earned by lending to risky borrowers is not the same as a high NIM from a safe book — that's what the provision ratio is for

---

## Efficiency Ratio

**What it is:** Non-interest expense (salaries, IT, buildings — the running costs) divided by total revenue. The bank equivalent of an inverse operating margin.

**Why it matters:** It answers a simple question: how many cents does the bank spend to produce one dollar of revenue? It's the cleanest single read on operational discipline.

**How to read it:**
- **Lower is better** — this is the one bank metric where down is good
- ~55–60% is typical for a large bank; JPM running toward ~52–55% is strong
- A falling trend (as JPM shows over the decade) means the bank is getting more efficient — more revenue per dollar of cost

**Where it lies:**
- The denominator (total revenue) swings with the rate environment. A rate-driven revenue jump flatters the ratio without any real efficiency gain — the bank just earned more, not spent less
- It lumps all non-interest expense together, so it can't distinguish a bank investing in growth (tech, hiring) from one that's simply bloated
- Not comparable across bank *types* — an investment bank and a retail bank have structurally different cost bases

---

## Return on Assets (ROA)

**What it is:** Net income divided by total assets. What the bank earns on every dollar of balance sheet.

**Why it matters:** For a bank, ROA is often more honest than ROE. ROE can be inflated simply by piling on leverage; ROA can't, because the denominator is the *whole* balance sheet. It's the cleaner read on underlying profitability.

**How to read it:**
- The range is small — a healthy bank ROA sits around ~1%–1.5%. JPM near ~1.2% is solid
- Do not read it like a tech ROA. 1.2% is *good* for a bank; the same number would be alarming for a software company
- Rising ROA over time (as JPM shows) signals genuine profitability improvement, not just leverage games

**Where it lies:**
- The absolute number is meaningless without context — always compare a bank to other banks, never to non-financials
- ROA and ROE together tell you about leverage: if ROE is high but ROA is ordinary, the returns are being manufactured by the balance-sheet size, not by superior earning power

---

## Equity / Assets

**What it is:** Shareholders' equity divided by total assets. The simplest possible read on how thick the bank's capital cushion is — effectively the inverse of leverage.

**Why it matters:** A bank funds enormous assets with a thin sliver of equity. This ratio shows how thin. It's a poor-man's stand-in for the regulatory Tier-1 ratio (which usually isn't cleanly available in standard XBRL).

**How to read it:**
- Higher means a thicker safety buffer; JPM around ~7.4% implies roughly 13–14x leverage
- For a large, trading-heavy bank this level is normal; a small retail bank might run higher
- A falling ratio means rising leverage — more assets stacked on the same equity

**Where it lies:**
- This is *not* the real regulatory capital ratio. It uses raw book equity and total assets, not risk-weighted assets or Tier-1 capital. It's a rough proxy, not a compliance figure
- It treats all assets as equally risky, which they aren't. A balance sheet full of government bonds is far safer at the same ratio than one full of unsecured loans

---

## Provision for Credit Losses / Revenue

**What it is:** The amount a bank sets aside for expected loan losses, relative to revenue. A forward-looking read on credit quality.

**Why it matters:** Provisions are one of the earliest signals of stress. A bank raises them *before* losses actually materialise, when it senses trouble in the loan book — so a rising provision ratio can lead a downturn.

**How to read it:**
- Low and stable in good times (low single-digit % of revenue)
- Spikes in a crisis — JPM's ~18–20% during COVID 2020 is the bank bracing for a wave of defaults
- **Can go negative** — JPM's ~-8% in 2021 is *reserve release*: money set aside in 2020 flowed back into profit once the feared defaults didn't happen. A negative provision ratio is a *good* sign

**Where it lies:**
- Highly discretionary. Provisioning involves management judgement about the future, so it can be used to smooth earnings — under-provisioning in good times to flatter profits, over-provisioning to build a cushion
- The sign flips the intuition: a *rising* ratio isn't necessarily bad if the bank is prudently getting ahead of risk, and a falling one isn't always good if it's just running reserves thin

---

## P/TBV — Price to Tangible Book Value

**What it is:** Market cap divided by tangible book value (equity minus goodwill). For banks it replaces plain P/B as the primary valuation-to-book measure.

**Why it matters:** Banks are valued off book value, but plain book value is inflated by goodwill from past acquisitions — an accounting entry, not hard capital you could recover in a crisis. P/TBV strips it out, leaving the tangible equity that actually backs the business.

**How to read it:**
- Higher than the plain P/B by construction (goodwill is removed from the denominator) — JPM's P/TBV of ~2.95 vs. a P/B of ~2.53 shows goodwill is roughly 15% of equity
- Read against the bank's *own* history: JPM re-rating from ~1.2 (2022) to ~2.9 shows the market repricing it upward
- A P/TBV near 1.0 means the market values the bank at roughly its liquidation-adjusted net worth; well above 1.0 means it's paying for future earning power

**Where it lies:**
- Our version subtracts only goodwill, not other intangibles. For JPM those are trivial (low single-digit billions on a ~4tn balance sheet), but for an intangible-heavy institution the tangible book would be overstated
- Book value itself is an accounting number. In a stressed bank, the "tangible" book can still evaporate if the asset marks are wrong — P/TBV assumes the balance sheet is honestly valued

---

## P/PPNR — Price to Pre-Provision Net Revenue

**What it is:** Market cap divided by pre-provision net revenue (net interest income + non-interest income − non-interest expense). PPNR is the bank's earning power *before* credit costs and taxes — the clean analogue to EBITDA for an industrial company.

**Why it matters:** It answers what EV/EBITDA answers for a normal company — how the market prices the underlying operating engine — but without the EV problem (enterprise value is conceptually broken for banks, since deposits are the raw material, not a financing layer). PPNR is a standard measure, used by the Fed in its bank stress tests.

**How to read it:**
- Lower than P/E by construction, because PPNR is larger than net income (it's before provisions and tax) — JPM's P/PPNR averaging ~7.6 vs. a P/E of ~10.4
- Read against the bank's own history; the 2023 trough (~5.5) reflects the rate-scare episode, the 2024–26 rise mirrors the same re-rating seen in P/E and P/TBV
- Useful precisely *because* it's before provisions: it isolates operating strength from the noise of a single year's credit cycle

**Where it lies:**
- By ignoring provisions entirely, it flatters a bank that's under-reserving. A bank can have a great PPNR and still be heading for trouble if its loan book is deteriorating — pair it with the provision ratio
- It's pre-tax, so it ignores differences in tax efficiency between banks
- PPNR isn't a single reported line — it's assembled from three components, so it inherits any tagging quirks in those inputs

---

## Combined Ratio; the following metrics can be used for insurance_pc

**What it is:** (Incurred losses + underwriting expenses) divided by earned premiums —
`BenefitsLossesAndExpenses / EarnedPremiums`. The single most important number in P&C insurance.

**Why it matters:** It answers the most basic question about an insurer: does it make money
*just from underwriting*, before any investment income is added in? A combined ratio below
100% means yes — the company would be profitable even if its investment portfolio earned
nothing. Above 100% means the underwriting side loses money and the company is relying on
investment income to stay profitable overall.

**How to read it:**
- **Lower is better** — this is the one insurance metric where under 100% is the pass/fail line
- Below 95%: strong underwriting discipline
- 95–100%: profitable but not exceptional
- Above 100%: underwriting loss, common in years with major catastrophes (hurricanes, wildfires)
- TRV's own history shows this clearly: it spiked above 109% in 2012 (a heavy catastrophe year)
  and has run in the 89–96% range more recently — reading the trend matters more than any single
  quarter

**Where it lies:**
- There's no XBRL tag for "combined ratio" — it's computed here from two components, not pulled
  from a single reported line. It should closely match what the company itself discloses (verified
  against TRV's own reported figures), but always sanity-check a new ticker's value against its own
  investor materials before trusting it blindly
- A single quarter's combined ratio can be swung heavily by one large event (a hurricane, a
  reserve adjustment) — read it as a trend, not a single-period verdict
- It says nothing about *how* the number was achieved — a low combined ratio from aggressively
  raising prices isn't the same as one from genuinely better risk selection

---

## Loss Ratio

**What it is:** Incurred losses divided by earned premiums — the claims-only half of the combined
ratio, with the expense side stripped out.

**Why it matters:** It isolates *underwriting risk selection* from *cost efficiency*. A company
can have a mediocre combined ratio for two very different reasons — bad pricing/risk selection
(high loss ratio) or bloated operations (high expense ratio) — and the loss ratio tells you which
one it is.

**How to read it:**
- Typically the larger of the two components — TRV's loss ratio runs roughly double its expense
  ratio
- Rising loss ratio with a stable expense ratio points to worsening claims experience (more
  frequent or more severe claims, or prices that haven't kept up with claim cost inflation)
- Compare it against the expense ratio's trend, not in isolation — see Expense Ratio below

**Where it lies:**
- Like the combined ratio, single-quarter spikes are normal in a catastrophe-exposed business and
  don't necessarily signal a structural problem
- A "good" loss ratio depends heavily on the line of business — auto, homeowners, and commercial
  liability all run at structurally different loss ratios, so this is much more useful compared to
  a company's *own* history than across unrelated insurers

---

## Expense Ratio (Insurance)

**What it is:** The underwriting-cost share of the combined ratio — computed here as
`combined ratio − loss ratio`, since no single tag captures total underwriting expense cleanly.

**Why it matters:** It's the pure efficiency read on the underwriting operation: commissions,
policy acquisition costs, and administrative overhead, all relative to premium volume.

**How to read it:**
- **Lower is better**, same direction as the combined ratio
- A steadily *falling* expense ratio (as seen in TRV's own multi-year trend) signals genuine
  operating leverage — the same premium base is being serviced more cheaply over time
- Unlike the loss ratio, this one is much less affected by any single catastrophe event, so a
  sudden jump here is more likely a real cost problem than bad luck

**Where it lies:**
- Because it's computed as a residual (combined minus loss), any error in either of the two
  source ratios flows directly into this one — it inherits both of their data-quality caveats
  rather than having its own independent verification
- Don't confuse "insurance expense ratio" with a normal company's operating-expense ratio; they
  measure conceptually different things and aren't comparable across those two contexts

---

## Net Investment Yield

**What it is:** Net investment income divided by total invested assets — how much return the
insurer earns on the pool of capital backing its policies (the "float").

**Why it matters:** This is an insurer's second profit engine, separate from underwriting. A
company with a mediocre combined ratio can still be a good business if it invests its float
skillfully; conversely, a great underwriter with a poorly-run investment book leaves money on
the table.

**How to read it:**
- Typically in the 3–5% range for a conservatively-invested P&C book (mostly high-grade bonds)
- Moves with the broader interest-rate environment more than with anything company-specific — a
  rise from ~3% to ~4% across the industry usually reflects rates generally, not a change in
  investment skill
- TRV's own yield dipped toward ~2.7% during the zero-rate years and climbed back above 4% as
  rates rose — read this alongside the macro rate backdrop, not as a standalone skill signal

**Where it lies:**
- The denominator here is total investments, not risk-adjusted or duration-matched assets — two
  companies with the same yield can carry very different levels of interest-rate or credit risk
  to get there
- Doesn't capture unrealized gains/losses sitting in the portfolio, only the income actually
  earned and recognized

---

## Reserve Growth

**What it is:** Year-over-year growth in the liability for unpaid claims and claims adjustment
expense — how fast the insurer's loss reserves are increasing.

**Why it matters:** Reserves are the company's own estimate of what it will eventually have to
pay out on claims already incurred but not yet settled. Watching how this estimate changes over
time is one of the earliest available signals of developing claims trouble — the bank-world
equivalent of the provision ratio.

**How to read it:**
- Reserves growing roughly in line with premium growth is normal and expected
- Reserves growing meaningfully *faster* than premiums can indicate the company is having to set
  aside more for claims than its pricing assumed — a warning sign worth investigating further
- Reserves growing *slower* than premiums (as seen in TRV's own history) is generally a good
  sign — reflects genuine growth without a matching escalation in claims liability
- Can occasionally go negative — reserves do shrink when old claims settle for less than
  reserved, or a book of business runs off

**Where it lies:**
- Reserve levels involve real actuarial judgment, not a hard fact — a company can be
  under-reserving in good times to flatter earnings, and this metric alone won't distinguish
  "genuinely improving claims experience" from "reserves quietly being run too thin"
- Only tells you about the balance, not why it changed — a reserve increase could be organic
  claims development or simply the addition of a new, larger book of business

---

## P/TBV (Insurance)

**What it is:** Same construction as the banking version — market cap divided by tangible book
value (equity minus goodwill) — replacing P/B as the primary book-value valuation metric for
this profile.

**Why it matters:** Insurers, like banks, are valued largely against their book value, since
that book directly represents the capital backing future claims-paying ability. Stripping out
goodwill (an accounting artifact from past acquisitions, not real claims-paying capital) gives a
cleaner read than plain P/B.

**How to read it:** Same logic as the banking version — read against the company's own history,
and expect it to run modestly higher than P/B for a company with real goodwill on the books
(TRV's P/TBV runs a bit above its P/B, reflecting its ~$4B of goodwill against ~$33B of equity).

**Where it lies:** Only goodwill is stripped out here, not other intangibles — fine for a company
like TRV where goodwill dominates any intangible balance, but worth checking before trusting this
blindly on an insurer with a large separately-tagged intangible-asset base.

---

## P/Core Operating Earnings

**What it is:** Market cap divided by net income with realized investment gains and losses
removed — `market_cap / (NetIncome_TTM − RealizedInvestmentGains_TTM)`. The insurance analogue
to a bank's P/PPNR: a valuation multiple built on an earnings base cleaned of market noise.

**Why it matters:** GAAP net income for an insurer includes realized gains and losses on its
investment portfolio, which are driven by market timing and portfolio decisions, not by how well
the company underwrote risk or managed its float that quarter. A large one-off realized gain (or
loss) can make P/E look artificially cheap (or expensive) for a quarter that says little about
ongoing earning power.

**How to read it:** Should sit close to, but not identical to, the plain P/E — the gap between
the two is a direct measure of how much of reported earnings came from realized investment
trading rather than core operations. A small, stable gap (as seen in TRV, where the two multiples
track closely) suggests realized gains/losses are a minor, non-distorting factor for that company.

**Where it lies:**
- Only removes *realized* gains/losses — unrealized mark-to-market moves sitting in book value
  aren't touched by this at all
- Like PPNR, this is assembled from raw tag data rather than a single reported line, so it
  inherits whatever tagging gaps exist in its inputs — verify the underlying `RealizedInvestment
  Gains` tag has clean, continuous coverage for a given ticker before trusting this multiple on it

---

## Inventory turnover; following metrics are retail only

**What it is:** Cost of goods sold divided by inventory on hand. How many times per year the company sells through its entire stock of merchandise.

**Why it matters:** Inventory is capital sitting on a shelf. The faster it turns, the less cash is tied up doing nothing, and the less exposure to markdowns, spoilage, or obsolescence. For a retailer, this is one of the purest measures of operational discipline.

**How to read it:**
- The absolute level is only meaningful *within a business type*. Off-price and grocery-adjacent retailers turn inventory 8–12x a year; specialty/luxury retailers with slower-moving, higher-margin goods might turn 2–4x. Comparing across these is like comparing operating margins across software and supermarkets — it tells you they're different businesses, not which is better run
- The **trend** matters more than the level. A falling turnover ratio over several quarters usually means unsold goods are piling up — a leading indicator of future markdowns
- Watch this alongside revenue growth: turnover falling while revenue grows can mean the company is over-ordering ahead of demand that isn't materializing

**Where it lies:** This tool uses the inventory balance at period-end, not an average of the period. A retailer's inventory level right before a big seasonal restock (e.g. a quarter-end that lands just before holiday season) will look artificially low-turnover for that one snapshot — that's a timing artifact, not a real change in efficiency. It also can't tell you whether the inventory sitting there is fresh and sellable or quietly going stale; the tag just counts dollars, not shelf life.

---

## Days Inventory Outstanding (DIO)

**What it is:** The same idea as inventory turnover, restated as a time span instead of a ratio — roughly how many days, on average, a unit of merchandise sits before it's sold.

**Why it matters:** "2.4x turnover a year" is an abstract ratio; "150 days" is something you can intuitively picture. This is also the building block for the cash conversion cycle below.

**How to read it:** Lower generally means leaner, faster-moving operations — but again, only within the same kind of business. A grocery-adjacent retailer at 150 days would be a red flag; a luxury goods retailer at 150 days might be completely normal.

**Where it lies:** Same period-end snapshot issue as inventory turnover above. Also sensitive to genuine mix shift — a retailer expanding into a category that naturally holds inventory longer (say, moving from apparel into furniture) will show DIO rising even though nothing about its execution has gotten worse. Check what's actually being sold before reading a DIO increase as decay.

---

## Days Sales Outstanding (DSO)

**What it is:** Accounts receivable divided by revenue, restated in days — how long, on average, the company waits between a sale and actually collecting the cash for it.

**Why it matters:** Revenue booked isn't the same as cash collected. A rising DSO means more of the top line exists as an IOU rather than money in the bank.

**How to read it:**
- For a pure cash-and-card consumer retailer, this should sit near zero — there's no meaningful gap between the sale and the cash
- A real, non-trivial DSO at a consumer-facing retailer usually means a genuine secondary channel exists — commercial accounts, trade credit to business customers, a private-label credit program — not a data error. Several retailers that look like simple consumer retailers on the surface carry real receivables for exactly this reason; check what the business actually sells before assuming DSO should be zero
- A DSO that's rising over time, especially alongside slowing organic growth, can mean the company is loosening credit terms to keep sales numbers up — a classic way to disguise decelerating demand for a few quarters

**Where it lies:** This metric can't distinguish "healthy, growing B2B channel" from "generous terms propping up a weakening core business." Cross-check against revenue growth and margin trends before drawing a conclusion either way.

---

## Days Payable Outstanding (DPO)

**What it is:** Accounts payable divided by cost of goods sold, restated in days — how long, on average, the company takes to pay its own suppliers.

**Why it matters:** Every day a bill goes unpaid, the company is effectively using its supplier's cash instead of its own. This is interest-free financing, and how much of it a company can command says a lot about its negotiating leverage.

**How to read it:**
- Higher is generally favorable for the retailer — it's holding onto cash longer
- Large, scaled retailers can typically command longer payment terms simply because of their purchasing volume; a smaller competitor with a lower DPO isn't necessarily worse-run, it may just have less leverage over the same suppliers
- A DPO that's rising sharply alongside weak or falling free cash flow margin is a different story — that can mean the company is stretching payments because it's short on cash, not because it's negotiating well. Read DPO next to `fcf_margin`, not in isolation

**Where it lies:** A high DPO driven by genuine negotiating power and a high DPO driven by cash-flow stress can look identical in the number alone. The company's cash flow trend is what tells them apart.

---

## Cash Conversion Cycle (CCC)

**What it is:** DIO + DSO − DPO. The net number of days between the company paying cash out for inventory and collecting cash in from selling it — after accounting for how long it strung out its own suppliers in between.

**Why it matters:** This is the single cleanest summary of how much working capital a retail business actually ties up to operate. A short cycle means the business is close to self-funding; a long one means growth requires ongoing external capital just to stock the shelves.

**How to read it:**
- Lower is better; shorter cycles mean less capital trapped in day-to-day operations
- A **negative** CCC — where supplier payment terms are longer than the time it takes to sell the inventory and collect the cash — means the customer's money effectively arrives before the company ever has to pay for the goods it sold them. This is one of the more powerful structural traits a retail business can have, seen in a few of the tightly-run specialty retailers in this dataset
- Compare within the same business type, same as its three components

**Where it lies:** Inherits every caveat from DIO, DSO, and DPO above. It's also a blended number — a DIO that's quietly getting worse and a DPO that's improving for unrelated reasons can offset each other and produce a flat, unremarkable CCC that hides two real, opposite-direction stories underneath. If the CCC looks static for several quarters, check its three components individually before assuming nothing is changing.

---

# Part 3: How to actually use this

**Start with the fundamentals chart.** Ignore the price entirely. Is revenue growing? Are margins stable or improving? Is the debt manageable? Is free cash flow real? If the answer to any of these is a clear no, the valuation doesn't matter — you can stop.

**Then look at the valuation chart.** For each multiple, ask only one question: *where is the line relative to its own five-year average?* You are not looking for "cheap"; you are looking for "cheaper than this business has typically been priced".

**Then ask why.** If a stock is well below its historical multiples, the market has changed its mind about something. Your job is to figure out what, and whether the market is right. A stock is rarely cheap by accident.

**Cross-check the metrics against each other.** P/E and P/FCF disagreeing means profits aren't turning into cash. High ROE with high debt/equity means the returns are borrowed, not earned. Rising revenue with falling margins means growth is being bought. The contradictions are where the information is.

**Know what the numbers can't tell you.** None of this captures management quality, competitive threats, regulatory risk, technological obsolescence, or whether the product is any good. Every figure here is a rear-view mirror. They tell you what happened and what the market currently believes. They do not tell you what happens next.

---

**This is an analysis tool, not investment advice.** It computes ratios from public filings. Every judgment about what those ratios mean for any particular decision is yours.
