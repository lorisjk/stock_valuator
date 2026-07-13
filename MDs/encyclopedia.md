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

# Part 3: How to actually use this

**Start with the fundamentals chart.** Ignore the price entirely. Is revenue growing? Are margins stable or improving? Is the debt manageable? Is free cash flow real? If the answer to any of these is a clear no, the valuation doesn't matter — you can stop.

**Then look at the valuation chart.** For each multiple, ask only one question: *where is the line relative to its own five-year average?* You are not looking for "cheap"; you are looking for "cheaper than this business has typically been priced".

**Then ask why.** If a stock is well below its historical multiples, the market has changed its mind about something. Your job is to figure out what, and whether the market is right. A stock is rarely cheap by accident.

**Cross-check the metrics against each other.** P/E and P/FCF disagreeing means profits aren't turning into cash. High ROE with high debt/equity means the returns are borrowed, not earned. Rising revenue with falling margins means growth is being bought. The contradictions are where the information is.

**Know what the numbers can't tell you.** None of this captures management quality, competitive threats, regulatory risk, technological obsolescence, or whether the product is any good. Every figure here is a rear-view mirror. They tell you what happened and what the market currently believes. They do not tell you what happens next.

---

**This is an analysis tool, not investment advice.** It computes ratios from public filings. Every judgment about what those ratios mean for any particular decision is yours.
