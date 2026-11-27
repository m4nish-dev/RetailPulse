# RetailPulse — Measure Audit History

> **HISTORICAL RECORD.** This summarises the measure audit of 2026-11-20 (fix-Phase 4)
> and its extension on 2026-11-27. The measures were then written in DAX for a Power BI
> design that the project has since retired: the dashboard is built in **Tableau Public**
> ([`../tableau/`](../tableau/README.md)). The detailed DAX audit files were removed with
> that design. The analytical findings below are tool-independent, and every one of them
> is built into the current Tableau calculated fields, which are validated against SQL by
> `scripts/validate_tableau_calcs.py`.

## What the audit did

The 49 original dashboard measures were each re-derived independently in SQL on the base
tables and compared with the measure's logic in several filter contexts (a month, a state,
a category, a seller, a segment, a cohort cell, an empty context). 41 measures were added
for the analytical sources and the specification visuals, giving the current catalogue of
**90 measures** (M01–M49, N01–N41). Every one still has SQL reference checks
(`scripts/sql_reference.py`, 223 contexts).

| Status of the 49 original measures | Count |
|---|---|
| Correct, unchanged | 32 |
| Correct; only the old check was wrong (it compared the median 86.90 with itself) | 1 |
| Formula bug fixed | 2 |
| Filter-context bug fixed | 8 |
| Weighting / grain bug fixed | 3 |
| Wrong source table fixed | 2 |
| Label clarified (counts seller-order pairs, not orders) | 1 |

Before the audit, 17 of the 49 measures had no real check.

## Errors found (each shown wrong before it was fixed)

| Area | What the wrong version did | Correct result |
|---|---|---|
| 3-month moving average | averaged **daily** revenue: 30,716 at 2018-03 | mean of three monthly totals: 921,468 |
| Month-over-month growth at 2017-01 | +1,101,719% against December 2016's single order | blank: only complete months are compared |
| Running total on a month axis | each "running total" was one month's revenue (429,917 at 2017-06) | cumulative: 2,065,044 |
| Jan–Aug YoY under a date filter | 2017 base filtered away, YoY blank | the YoY card ignores date filters |
| Customers per RFM segment | counted a table without a segment column: 96,096 in every segment | counted from the RFM source |
| Cohort retention at offset 1 | right-censored 2018-08 cohort in the denominator: 0.473% | observed cohorts only: 0.506% |
| Average item price | mean of product prices: 144.96 | revenue ÷ units: 120.38 |
| Seller late rate | mean of 3,053 seller rates, in percent units: 8.42 | weighted by seller-order pairs: 8.02% (platform per order: 8.11%) |
| Seller average delivery days | unweighted 12.21 | weighted 12.51 |
| Seller inherited order rating | unweighted 4.055 | weighted 4.099 |
| On-time rate with no deliveries | showed 100% | blank |
| Category review count at the total | 99,273, more reviews than exist (multi-category orders count in each category) | blank at totals |
| Category score method | item-weighted scores moved 5 of 34 categories across the average | review grain (Insight 14 revised to 15 of 34) |
| Revenue through a naive join | items × payments: 14,105,767.00 (+4.53%); items × reviews: 13,431,884.80 (−0.46%) | one-row-per-order views: 13,494,400.74 |

## Where these rules live now

| Rule | Current implementation |
|---|---|
| Ratios are ratio-of-sums, never an average of per-group rates | seller fields M32, M33, M35; N11, N15, N16 |
| Growth and moving averages only over complete months | M10, M11 (`in_stable_window`, `DATEDIFF` guard) |
| Non-additive values blank at totals | N29–N33 (`COUNTD(category) = 1`), N05 (single offset) |
| Unobserved cohort cells blank, never 0 | N05; `scripts/check_tableau_data.py` |
| Revenue never multiplied by joins | Tableau relationships at native grain; 7 fan-out guards; pitfall P05 |

Formulas, definitions and expected values: [`../tableau/calculated_fields.md`](../tableau/calculated_fields.md).
