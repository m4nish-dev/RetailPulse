# Business Questions

**Version 1.0** · 2026-11-12
**Status:** questions defined and confirmed answerable. **No answers yet** —
those come from Phases 4, 5 and 7.

Each question below was checked against the profiled data: the columns exist,
the joins work, and the result will be meaningful. Questions the data *cannot*
honestly answer are listed at the end rather than quietly dropped.

**How to read the table:**
- **Priority** — P1 questions could change a business decision; P3 are useful context.
- **Tool** — where it gets answered.
- **Actionable?** — can a stakeholder actually *do* something with the answer?
  A question that only produces a number is worth less than one that produces a decision.

---

## A · Business performance

### Q1 — How has monthly revenue changed, and is growth accelerating or slowing?
**Priority:** P1 · **Tool:** SQL + Power BI · **Actionable:** Yes — sets targets and budget
**Method:** revenue by month over 2017-01 → 2018-08, with MoM growth via `LAG()`.
**Watch out:** the four edge months must be excluded or the chart implies a collapse.

### Q2 — How did 2018 perform against 2017 on a like-for-like basis?
**Priority:** P1 · **Tool:** SQL · **Actionable:** Yes — the headline growth claim
**Method:** Jan–Aug 2018 vs Jan–Aug 2017, revenue and orders.
**Watch out:** full-year YoY is impossible — 2016 has 329 orders.

### Q3 — Which states and cities generate the most revenue, and which are under-served relative to population?
**Priority:** P1 · **Tool:** SQL + Power BI map · **Actionable:** Yes — targets regional expansion
**Method:** revenue, orders and AOV by `customer_state`; concentration (what share do the top 3 states hold?).
**Watch out:** state-level only until city names are normalised.

### Q4 — Is Average Order Value rising or falling, and what sits behind the trend?
**Priority:** P2 · **Tool:** SQL · **Actionable:** Yes — informs bundling and free-shipping thresholds
**Method:** monthly AOV; decompose into items-per-order × price-per-item to see which moved.
**Watch out:** denominator must be orders *with items*; report median beside mean.

### Q5 — Is revenue seasonal, and which months need inventory and staffing planning?
**Priority:** P2 · **Tool:** SQL + Python · **Actionable:** Yes — operational planning
**Method:** monthly pattern across both years; check whether spikes repeat.
**Watch out:** only ~1.7 usable years, so "seasonality" is weakly evidenced. Say so.

---

## B · Customer behaviour & retention

### Q6 — What share of customers ever buy a second time, and what does that imply for strategy?
**Priority:** P1 · **Tool:** SQL + Python · **Actionable:** Yes — acquisition vs retention budget split
**Method:** repeat rate on `customer_unique_id`; distribution of orders per person.
**Why it matters:** profiling shows 3.12%. A marketplace that cannot retain
customers must either fix retention or accept a pure-acquisition model. That is
a strategic fork, and the number forces the conversation.

### Q7 — Do customers who return behave differently from one-time buyers?
**Priority:** P1 · **Tool:** SQL · **Actionable:** Yes — identifies what to encourage
**Method:** compare AOV, category mix, review score, delivery experience and
payment type between the 2,997 repeat customers and the 93,099 one-time buyers.
**Why it matters:** if repeat customers started in a particular category or had
a notably better first delivery, that is a lever.

### Q8 — Which customers are Champions, At Risk, or Lost, and how much revenue sits in each segment?
**Priority:** P1 · **Tool:** Python + Power BI · **Actionable:** Yes — directly targetable lists
**Method:** RFM (R and M by quintile, F as a 1/3/5 ordinal — see `kpi_definitions.md`).
**Watch out:** the F dimension is nearly degenerate; this must be stated.

### Q9 — Do cohorts acquired in later months retain better than earlier ones?
**Priority:** P2 · **Tool:** Python · **Actionable:** Partly — validates whether anything improved
**Method:** cohort by first-purchase month, retention in following months.
**Watch out:** curves will be very low and flat; later cohorts are right-censored.

### Q10 — Who are the highest-value customers, and how concentrated is revenue among them?
**Priority:** P2 · **Tool:** SQL · **Actionable:** Yes — justifies a VIP programme or shows one is pointless
**Method:** historical value per `customer_unique_id`; share held by the top 1% and 10%.
**Watch out:** label it historical value, never predicted CLV.

### Q11 — Does payment method relate to order value or repeat behaviour?
**Priority:** P3 · **Tool:** SQL · **Actionable:** Partly — informs checkout and instalment options
**Method:** AOV, instalment count and repeat rate by `payment_type`.
**Why it matters:** boleto is 19% of payments and behaves differently from cards.

---

## C · Product & category performance

### Q12 — Which categories drive revenue, and how concentrated is the business?
**Priority:** P1 · **Tool:** SQL + Power BI · **Actionable:** Yes — merchandising and marketing focus
**Method:** revenue, orders and AOV by English category name; cumulative contribution curve.
**Watch out:** LEFT JOIN the translation table; `unknown` holds 610 products.

### Q13 — Which categories are growing and which are declining?
**Priority:** P1 · **Tool:** SQL · **Actionable:** Yes — where to invest or withdraw
**Method:** monthly revenue per category inside the stable window; compare first and last quarter.

### Q14 — Which products sell often but cheaply, and which sell rarely but at high value?
**Priority:** P2 · **Tool:** SQL · **Actionable:** Yes — pricing and promotion strategy
**Method:** order frequency against average price per product; quadrant analysis.
**Watch out:** apply a minimum order threshold or the long tail dominates.

### Q15 — Do some categories consistently receive poor reviews?
**Priority:** P1 · **Tool:** SQL · **Actionable:** Yes — category-level quality intervention
**Method:** average review score and 1-star share by category, with a minimum order threshold.
**Why it matters:** links Module 3 and Module 6 — a revenue-heavy category with
poor ratings is a quantifiable risk.

---

## D · Seller performance

### Q16 — How dependent is the marketplace on its largest sellers?
**Priority:** P1 · **Tool:** SQL · **Actionable:** Yes — concentration risk
**Method:** share of revenue from the top 1%, 10% and 50% of sellers.
**Why it matters:** profiling shows one seller on 2,033 order items out of
3,095 sellers. If a handful carry the platform, losing one is a material event.

### Q17 — Which sellers combine high volume with poor delivery or poor ratings?
**Priority:** P1 · **Tool:** SQL + Power BI scorecard · **Actionable:** Yes — a named intervention list
**Method:** composite scorecard — revenue, order count, average delivery days,
late rate, average review score. Minimum 20 orders to qualify.
**Watch out:** reviews are order-level; in multi-seller orders every seller
inherits the score. Delay is not solely the seller's fault.

### Q18 — Does a seller's location explain delivery performance?
**Priority:** P2 · **Tool:** SQL · **Actionable:** Yes — warehouse and fulfilment placement
**Method:** average delivery days by seller state, and by seller-state → customer-state pair.

---

## E · Delivery operations

### Q19 — How accurate are the delivery estimates given to customers?
**Priority:** P1 · **Tool:** SQL + Python · **Actionable:** Yes — a concrete promise-setting change
**Method:** distribution of `delay_days` (actual − estimated), not just the pass rate.
**Why it matters:** profiling shows 91.9% "on time" but an average arrival
**11 days early**. That pattern suggests deliberately padded estimates rather
than fast delivery. If true, Olist is losing conversions by quoting pessimistic
dates — a finding with a clear, testable action behind it. **This is one of the
strongest questions available in this dataset.**

### Q20 — Where and when do late deliveries concentrate?
**Priority:** P1 · **Tool:** SQL + Power BI · **Actionable:** Yes — targeted logistics fixes
**Method:** late rate by customer state, by month, and by distance proxy (seller state → customer state).

### Q21 — Which stage of the journey consumes the most time?
**Priority:** P2 · **Tool:** SQL · **Actionable:** Yes — identifies the real bottleneck
**Method:** split delivery into purchase→approval, approval→carrier, carrier→customer.
**Why it matters:** if the delay is in approval rather than shipping, the fix is
in payments, not logistics.

### Q22 — Does freight cost vary unreasonably by region or order value?
**Priority:** P2 · **Tool:** SQL · **Actionable:** Yes — pricing and free-shipping thresholds
**Method:** freight as a share of item price, by state and by price band.
**Watch out:** this is freight charged, not Olist's cost.

---

## F · Customer satisfaction

### Q23 — How much does late delivery actually cost in customer satisfaction?
**Priority:** P1 · **Tool:** SQL + Python · **Actionable:** Yes — quantifies the delivery investment case
**Method:** average review score bucketed by `delay_days`; 1-star share for
on-time versus late orders.
**Why it matters:** turns "we should improve delivery" into "late orders average
X stars versus Y for on-time, affecting Z orders." That is a business case.
**Watch out:** correlation, not causation.

### Q24 — What drives one-star reviews beyond delivery?
**Priority:** P1 · **Tool:** SQL + Python · **Actionable:** Yes — prioritises fixes
**Method:** compare 1-star orders against the baseline on delivery delay,
category, seller, price band and freight ratio.

### Q25 — Has customer satisfaction improved or declined over time?
**Priority:** P2 · **Tool:** SQL · **Actionable:** Yes — tracks whether anything is working
**Method:** monthly average review score and 1-star share across the stable window.

### Q26 — Do review comments reveal themes the scores do not? *(optional)*
**Priority:** P3 · **Tool:** Python NLP · **Actionable:** Partly
**Method:** keyword and theme extraction from the 41,000 non-null comments.
**Watch out:** text is Portuguese. Needs a multilingual model or translation.
Genuinely optional — the project is complete without it.

---

## Priority summary

| Priority | Count | Questions |
|---|---|---|
| **P1** — could change a decision | 15 | Q1, Q2, Q3, Q6, Q7, Q8, Q12, Q13, Q15, Q16, Q17, Q19, Q20, Q23, Q24 |
| **P2** — valuable context | 9 | Q4, Q5, Q9, Q10, Q14, Q18, Q21, Q22, Q25 |
| **P3** — nice to have | 2 | Q11, Q26 |

**Total: 26 questions**, all confirmed answerable from the profiled data.

The strongest candidates for Phase 7's headline insights are **Q6** (3% repeat
rate forces a strategic choice), **Q19** (padded delivery estimates), **Q23**
(the cost of lateness in satisfaction) and **Q16** (seller concentration risk) —
each produces a number attached to a decision rather than a number on its own.

---

## Questions this dataset cannot answer

Listed so they are never attempted and never faked.

| Question | Why not |
|---|---|
| Which products are most profitable? | No cost or COGS column exists |
| What is a customer's predicted lifetime value? | 3.12% repeat rate gives no basis for prediction |
| What does it cost to acquire a customer? | No marketing spend data |
| Which marketing channels work? | No channel or attribution data |
| Why did customers abandon their carts? | Only completed orders are recorded |
| What is the return or refund rate? | Not recorded; no negative values anywhere |
| How do different demographics behave? | Data is anonymised — no age, gender or income |
| What is stock availability? | No inventory table |
| How do customers navigate the site? | No clickstream data |
