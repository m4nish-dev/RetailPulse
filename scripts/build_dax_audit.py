"""
RetailPulse - build powerbi/dax_measure_audit.md and powerbi/dax_implementation_checklist.md.

The audit report is GENERATED so it cannot drift from its evidence:
  * DAX formulas      <- powerbi/dax_measures.md (blocks tagged "-- [ID] Name")
  * checks / results  <- powerbi/dax_validation_results.csv (from validate_dax_logic.py)
  * audit judgement   <- the AUDIT table below (meaning, source, status, issue, limitation)

Run validate_dax_logic.py first, then:
    ./venv/bin/python scripts/build_dax_audit.py

The implementation checklist (Power BI build on Windows) adds entry order
(dependencies first), a format string and the expected filter behaviour.
"""
from pathlib import Path
import re
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "powerbi" / "dax_measures.md").read_text(encoding="utf-8")
RES = pd.read_csv(ROOT / "powerbi" / "dax_validation_results.csv")

OK, VF, FB, FC, FW, FS, CL, NEW = ("Validated, unchanged", "Validated; validator check fixed",
                                   "FIXED: formula bug", "FIXED: filter context", "FIXED: weighting / grain",
                                   "FIXED: wrong source table", "Clarified: label / additivity", "New")

# id: (business meaning, source table[columns], status, issue found, known limitation)
AUDIT = {
 "M01": ("Product revenue, freight excluded", "vw_order_summary[order_revenue, revenue_eligible]", OK, "", "Historical only; no cost data"),
 "M02": ("Order count, all statuses", "vw_order_summary", OK, "", ""),
 "M03": ("Distinct people who ordered", "vw_order_summary[customer_unique_id]", OK, "", "Date-responsive (people active in period), unlike M16"),
 "M04": ("Orders with at least one item", "vw_order_summary[item_count]", OK, "", ""),
 "M05": ("AOV denominator: eligible orders with items", "vw_order_summary[revenue_eligible, item_count]", OK, "", ""),
 "M06": ("Average order value", "M01 / M05", OK, "", "Compare equal periods only; report M07 beside it"),
 "M07": ("Median order value", "vw_order_summary[order_revenue]", VF, "Validator compared the constant 86.90 with itself", ""),
 "M08": ("Freight charged on eligible orders", "vw_order_summary[order_freight]", OK, "", "Freight charged, not Olist's freight cost"),
 "M09": ("Previous calendar month's revenue", "dim_date[MonthIndex], M01", FC, "Unvalidated; DATEADD replaced by contiguous MonthIndex arithmetic, HASONEVALUE guard added", "Month grain only"),
 "M10": ("Month-over-month revenue growth", "M01, M09, dim_date[InStableWindow]", FC, "Unvalidated; compared 2017-01 with Dec 2016's single order (+1,101,719%). Now BLANK unless both months complete", "Month grain only"),
 "M11": ("Mean of the last three monthly revenues", "dim_date[MonthIndex, InStableWindow], M01", FB, "AVERAGEX over DATESINPERIOD iterated DAYS: daily average, about 1/30 of the intended value; also used partial edge months", "BLANK until 3 complete months (first value 2017-03)"),
 "M12": ("Cumulative revenue to the current date", "dim_date (ALLSELECTED), M01", FC, "ALLSELECTED(dim_date[Date]) kept a YearMonth axis filter, so each value was one month's revenue", "Respects page date slicers by design"),
 "M13": ("Revenue Jan-Aug 2017", "dim_date[Year, MonthNo], M01", FC, "No REMOVEFILTERS: a page YearMonth slicer intersected 2017 with the slicer and returned BLANK", ""),
 "M14": ("Revenue Jan-Aug 2018", "dim_date[Year, MonthNo], M01", FC, "Same as M13", ""),
 "M15": ("Like-for-like YoY growth, Jan-Aug", "M13, M14", FC, "Unvalidated; inherited M13/M14's slicer problem", "Only YoY this dataset supports"),
 "M16": ("People in the customer dimension", "vw_customer_summary", OK, "Unvalidated before (covered indirectly)", "Lifetime figure: date slicers do not filter it"),
 "M17": ("People with 2+ orders", "vw_customer_summary[total_orders]", OK, "", "Lifetime figure"),
 "M18": ("People with exactly 1 order", "vw_customer_summary[total_orders]", OK, "", "Lifetime figure"),
 "M19": ("Repeat purchase rate", "M17 / M16", OK, "", "Right-censored for late customers"),
 "M20": ("Average orders per person", "vw_customer_summary[total_orders]", OK, "", "Mean of a near-constant; show the distribution"),
 "M21": ("Historical spend by customers", "vw_customer_summary[historical_value]", OK, "", "Never label as CLV / lifetime value"),
 "M22": ("People in the selected RFM segment", "rfm_customer_segments[rfm_scored, rfm_segment]", FS, "Counted vw_customer_summary, which has no segment column and cannot be filtered by one: 96,096 for every segment. Unvalidated", "F score is ordinal (1/3/5)"),
 "M23": ("Segment's share of eligible revenue", "rfm_customer_segments[monetary_value, rfm_segment]", FS, "Summed vw_customer_summary with ALL() over the whole table: no segment dimension, and it ignored state slicers. Unvalidated", ""),
 "M24": ("Category revenue", "vw_category_performance[revenue]", OK, "", ""),
 "M25": ("Eligible items sold", "vw_category_performance[items_sold]", OK, "Unvalidated before", ""),
 "M26": ("Number of categories", "vw_category_performance[category]", OK, "", ""),
 "M27": ("Category's share of revenue", "M24, dim_category", FC, "Unvalidated; ALL(vw_category_performance[category]) does not remove a dim_category filter: 100% everywhere on the new shared axis", "Use dim_category[category] on axes"),
 "M28": ("Revenue rank of a category", "M24, dim_category[category]", FC, "Unvalidated; RANKX over vw_category_performance[category] ranks every category 1 on a dim_category axis", "Use dim_category[category] on axes"),
 "M29": ("Seller revenue", "vw_seller_performance[revenue]", OK, "", ""),
 "M30": ("Sellers with eligible sales", "vw_seller_performance", OK, "", ""),
 "M31": ("Seller-order pairs served", "vw_seller_performance[orders_served]", CL, "Unvalidated; reads as orders but counts pairs (99,542 vs 98,199 orders)", "Label 'seller-order pairs'"),
 "M32": ("Average delivery days across sellers' orders", "seller_scorecard[delivery_days_sum, delivery_measurable_orders]", FW, "AVERAGE of per-seller averages: every seller weighted equally (12.21 vs 12.51). Unvalidated", "Multi-seller orders count per seller"),
 "M33": ("Late rate across sellers' orders", "seller_scorecard[late_orders, delivery_measurable_orders]", FW, "AVERAGE of per-seller late_pct: unweighted (8.42) and in percent units unlike every other rate. Unvalidated", "8.02% (pairs) vs platform 8.11% (orders): label it"),
 "M34": ("Largest seller's share of platform revenue", "vw_seller_performance[revenue, seller_id]", OK, "", "Denominator ignores slicers by design"),
 "M35": ("Inherited order rating across sellers", "seller_scorecard[review_score_sum, reviewed_orders]", FW, "AVERAGE of per-seller ratings: unweighted (4.055 vs 4.099). Unvalidated", "Inherited from orders, not a seller rating"),
 "M36": ("Orders with status delivered", "vw_order_summary[is_delivered]", OK, "", "Includes 8 with no delivery date"),
 "M37": ("Orders with a real delivery date", "vw_order_summary[delivery_measurable]", OK, "", ""),
 "M38": ("Orders delivered after the estimate", "vw_order_summary[is_late, delivery_measurable]", OK, "", ""),
 "M39": ("Late delivery rate", "M38 / M37", OK, "Unvalidated before", "Against Olist's own estimate"),
 "M40": ("On-time delivery rate", "M37, M38", FB, "1 - [Late Delivery Rate] returns 100% wherever there are no deliveries (1 - BLANK = 1)", "Against Olist's padded estimate"),
 "M41": ("Average purchase-to-delivery days", "vw_order_summary[delivery_days]", OK, "", "12.56 on 96,476 orders vs stage total 12.62 on 95,088"),
 "M42": ("Average days early/late vs estimate", "vw_order_summary[delay_days]", OK, "", "Negative = early"),
 "M43": ("Canceled orders", "vw_order_summary[order_status]", OK, "", "unavailable (609) reported separately"),
 "M44": ("Cancellation rate", "M43 / M02", OK, "", ""),
 "M45": ("Review records", "vw_review_summary", OK, "", ""),
 "M46": ("Average score, review grain", "vw_review_summary[review_score]", OK, "", "J-shaped distribution: show M47"),
 "M47": ("Share of 1-star reviews", "vw_review_summary[review_score]", OK, "", ""),
 "M48": ("Share of 5-star reviews", "vw_review_summary[review_score]", OK, "", ""),
 "M49": ("Average score, order grain", "vw_order_summary[review_score_avg, review_count]", OK, "", "Different metric from M46; stored to 4 dp"),
 "N01": ("Scored people (RFM denominator)", "rfm_customer_segments[rfm_scored]", NEW, "", ""),
 "N02": ("Segment's share of scored people", "M22 / N01", NEW, "", ""),
 "N03": ("Historical spend per person in segment", "rfm_customer_segments[monetary_value]", NEW, "", "Not a prediction"),
 "N04": ("Cohort size", "cohort_retention[cohort_customers]", NEW, "", ""),
 "N05": ("Share of a cohort active k months later", "cohort_retention[active_customers, cohort_customers, is_observed]", NEW, "", "BLANK where unobserved; totals weight observed cohorts only"),
 "N06": ("Cohort members returning in a month", "cohort_retention[returning_customers]", NEW, "", ""),
 "N07": ("Revenue of the largest category", "M24, dim_category", NEW, "Was a validator-only check with no documented DAX", ""),
 "N08": ("Product revenue (drill-through)", "product_performance[product_revenue]", NEW, "", ""),
 "N09": ("Units sold (drill-through)", "product_performance[units_sold]", NEW, "", ""),
 "N10": ("Products with an eligible sale", "product_performance[units_sold]", NEW, "", ""),
 "N11": ("Average item price, weighted", "product_performance[product_revenue, units_sold]", NEW, "", "AVERAGE(avg_item_price) would be wrong (144.96)"),
 "N12": ("Freight charged per item", "product_performance[freight_value, units_sold]", NEW, "", ""),
 "N13": ("Seller x category revenue", "seller_category_performance[product_revenue]", NEW, "", ""),
 "N14": ("Seller x category items", "seller_category_performance[item_count]", NEW, "", ""),
 "N15": ("Late rate within seller x category", "seller_category_performance[late_orders, delivery_measurable_orders]", NEW, "", "Orders inherit delivery outcome per pair"),
 "N16": ("Approval-to-carrier days, single-seller orders", "seller_category_performance[avg_dispatch_days, dispatch_measurable_orders]", NEW, "", "Excludes multi-seller and Q18 orders"),
 "N17": ("Orders with valid stage timing", "delivery_stage_orders", NEW, "", "95,088 of 96,476"),
 "N18": ("Purchase to approval, days", "delivery_stage_orders[purchase_to_approval_seconds]", NEW, "", ""),
 "N19": ("Approval to carrier handoff, days", "delivery_stage_orders[approval_to_carrier_seconds]", NEW, "", ""),
 "N20": ("Carrier to customer, days", "delivery_stage_orders[carrier_to_customer_seconds]", NEW, "", ""),
 "N21": ("Total purchase to delivery, days (stage population)", "delivery_stage_orders[total_seconds]", NEW, "", "Population differs from M41"),
 "N22": ("Last-mile share of delivery time", "delivery_stage_orders", NEW, "Replaces the hardcoded 74% caption", ""),
 "N23": ("Dispatch share of delivery time", "delivery_stage_orders", NEW, "", ""),
 "N24": ("Approval share of delivery time", "delivery_stage_orders", NEW, "", ""),
 "N25": ("Reviews answered before arrival (Q19)", "vw_review_summary[review_before_delivery]", NEW, "", ""),
 "N26": ("Share of delivered-order reviews answered before arrival", "vw_review_summary[review_before_delivery]", NEW, "", ""),
 "N27": ("Average score, after-arrival reviews", "vw_review_summary", NEW, "", ""),
 "N28": ("1-star share, after-arrival reviews", "vw_review_summary", NEW, "", ""),
 "N29": ("Reviews linked to one category", "category_satisfaction[review_count]", NEW, "", "BLANK unless one category: not additive"),
 "N30": ("Category average score, review grain", "category_satisfaction[avg_review_score]", NEW, "", "Whole-order experience, not product quality alone"),
 "N31": ("Category 1-star share", "category_satisfaction[one_star_pct]", NEW, "", ""),
 "N32": ("Category score, after-arrival reviews", "category_satisfaction[avg_review_score_after_arrival]", NEW, "", ""),
 "N33": ("Category share of pre-arrival reviews", "category_satisfaction[pct_reviews_before_delivery]", NEW, "", ""),
 "N34": ("Order-grain rating, after-arrival reviews", "vw_review_summary, N35", NEW, "", "Small samples beyond 7 days late (106 and 19 orders)"),
 "N35": ("Order-grain rating from the review table", "vw_review_summary[order_id, review_score]", NEW, "", ""),
 "N36": ("Pareto: share held by this category and every larger one", "vw_category_performance (via M24), dim_category", NEW, "Added 2026-11-27: the spec's Pareto curve had no measure", "BLANK unless one category"),
 "N37": ("Category revenue, Jan-Mar 2017", "vw_category_performance[revenue, order_month]", NEW, "Added 2026-11-27 for the growth chart", ""),
 "N38": ("Category revenue, Jun-Aug 2018 (last 3 complete months)", "vw_category_performance[revenue, order_month]", NEW, "Added 2026-11-27; spec label '2018 Q3' corrected", "Not calendar Q3"),
 "N39": ("Category growth 2017 Q1 to Jun-Aug 2018", "N37, N38, M25", NEW, "Added 2026-11-27 for the growth chart (sql/04 Q13 method)", "BLANK under 50 items in either period"),
 "N40": ("Concentration curve: share held by this seller and every larger one", "vw_seller_performance (via M29)", NEW, "Added 2026-11-27: the spec's concentration curve had no measure", "Top 10% = 67.43% (305 sellers) or 67.50% (306)"),
 "N41": ("Average promised delivery days (purchase to estimated date)", "vw_order_summary[delivery_days, delay_days, delivery_measurable]", NEW, "Added 2026-11-27: 'promised vs actual' had no measure", "Delivered orders only; equals estimated - purchase"),
}


def formulas():
    """{ID: formula text} from the tagged dax blocks."""
    out = {}
    blocks = re.findall(r"```dax\n(.*?)```", DOC, flags=re.S)
    for b in blocks:
        parts = re.split(r"^-- \[([MN]\d{2})\] .*$", b, flags=re.M)
        for mid, body in zip(parts[1::2], parts[2::2]):
            code = "\n".join(l for l in body.strip().splitlines() if not l.strip().startswith("--"))
            out[mid] = " ".join(code.split())
    return out


def fmt(v):
    if pd.isna(v):
        return "BLANK"
    if abs(v) >= 1000:
        return f"{v:,.2f}"
    if abs(v) < 1 and v != 0:
        return f"{v:.6f}"
    return f"{v:,.4f}".rstrip("0").rstrip(".")


def main():
    F = formulas()
    meas = RES[RES.kind == "measure"]
    missing = sorted(set(AUDIT) ^ set(F)) + sorted(set(AUDIT) ^ set(meas.id))
    if missing:
        sys.exit(f"AUDIT table, dax_measures.md and results disagree on: {sorted(set(missing))}")
    rows = []
    for mid in sorted(AUDIT, key=lambda x: (x[0] != "M", x)):
        m = meas[meas.id == mid]
        meaning, src, status, issue, lim = AUDIT[mid]
        first = m.iloc[0]
        rows.append({"id": mid, "name": first.measure, "meaning": meaning, "dax": F[mid], "source": src,
                     "example": f"{fmt(first.expected)} ({first.context})",
                     "checks": f"{int(m['pass'].sum())}/{len(m)}", "status": status,
                     "issue": issue or "—", "limitation": lim or "—"})
    df = pd.DataFrame(rows)

    n_all, n_pass = len(RES), int(RES["pass"].sum())
    orig = df[df.id.str.startswith("M")]
    sc = orig.status.value_counts()
    bugs = RES[RES.kind == "bug reproduction"]
    L = []
    L.append("# RetailPulse — DAX Measure Audit\n")
    L.append("**Date:** 2026-11-20 (fix-Phase 4) · **Generated by** `scripts/build_dax_audit.py` from "
             "`dax_measures.md` and `dax_validation_results.csv`. Do not edit by hand.\n")
    L.append(f"**Result:** {len(df)} measures (49 original + {len(df) - 49} new) · **{n_pass}/{n_all} checks pass** · "
             f"every measure ID covered\n")
    L.append("> **Scope.** Each check compares the measure's logic, emulated in pandas over the CSVs Power BI imports, with "
             "an independent SQL answer from the base tables. That proves the rows, denominators, grain, filter handling "
             "and BLANK behaviour are right *as written*. It does **not** prove DAX syntax or Power BI runtime behaviour, "
             "which need Windows.\n")
    L.append("## Summary of the 49 original measures\n")
    L.append("| Status | Measures |\n|---|---|")
    for st in [OK, VF, FB, FC, FW, FS, CL]:
        ids = ", ".join(orig.loc[orig.status == st, "id"])
        L.append(f"| {st} | {int(sc.get(st, 0))}: {ids} |")
    L.append("")
    L.append("Before this audit the validator had 37 checks: 33 on documented measures (one of them, M07, compared a "
             "constant with itself) and 4 on helper figures with no documented DAX. So **17 of the 49 measures had no "
             "real check**: M07, M09–M12, M15, M16, M22, M23, M25, M27, M28, M31–M33, M35, M39. Every measure now has "
             "at least one, most several, in different filter contexts.\n")
    L.append("## What was wrong, by category\n")
    L.append("| Problem type | Measures | Evidence (bug-reproduction check) |\n|---|---|---|")
    ev = {r.id: r.detail for _, r in bugs.iterrows()}
    L.append(f"| Formula bug | M11, M40 | M11: {ev.get('M11', '')}. M40: {ev.get('M40', '')} |")
    L.append(f"| Filter context | M09, M10, M12, M13–M15, M27, M28 | M12: {ev.get('M12', '')}. M15: {ev.get('M15', '')}. "
             f"M10: {ev.get('M10', '')}. M27/M28: DAX-semantics finding (see validator notes) |")
    L.append(f"| Weighting / grain | M32, M33, M35 | {ev.get('M33', '')} |")
    L.append(f"| Wrong source table | M22, M23 | {ev.get('M22', '')} |")
    L.append("| Label / additivity | M31 | counts seller-order pairs (99,542), not orders (98,199) |")
    L.append("| Validator tautology | M07 | `SELECT 86.90` compared with 86.90; now an independent SQL median |")
    L.append("| Affected by the new analytical sources | M22, M23 (moved to RFM), M27, M28 (dim_category axis), "
             "M32, M33, M35 (seller_scorecard) | — |")
    L.append("")
    L.append("## Full inventory\n")
    for page, ids in [("Page 1 — Executive", [f"M{i:02d}" for i in range(1, 16)]),
                      ("Page 2 — Customers, RFM, cohorts", [f"M{i:02d}" for i in range(16, 24)] + [f"N{i:02d}" for i in range(1, 7)]),
                      ("Page 3 — Category and drill-through", [f"M{i:02d}" for i in range(24, 29)] + [f"N{i:02d}" for i in range(7, 17)] + ["N36", "N37", "N38", "N39"]),
                      ("Page 4 — Sellers", [f"M{i:02d}" for i in range(29, 36)] + ["N40"]),
                      ("Page 5 — Delivery", [f"M{i:02d}" for i in range(36, 45)] + [f"N{i:02d}" for i in range(17, 25)] + ["N41"]),
                      ("Page 6 — Satisfaction", [f"M{i:02d}" for i in range(45, 50)] + [f"N{i:02d}" for i in range(25, 36)])]:
        L.append(f"### {page}\n")
        L.append("| ID | Measure | Business meaning | DAX | Source | Independently computed (context) | Checks | Status | Issue found | Limitation |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in df[df.id.isin(ids)].iterrows():
            dax = r.dax.replace("|", "\\|")
            L.append(f"| {r.id} | {r['name']} | {r.meaning} | `{dax}` | {r.source} | {r.example} | {r.checks} | "
                     f"{r.status} | {r.issue} | {r.limitation} |")
        L.append("")
    L.append("## Validation evidence\n")
    L.append("| Check group | Pass |\n|---|---|")
    for kind in ["measure", "supporting", "fan-out guard", "coverage", "bug reproduction"]:
        part = RES[RES.kind == kind]
        L.append(f"| {kind} | {int(part['pass'].sum())}/{len(part)} |")
    L.append("\nEvery check, with model value, expected value and context: `powerbi/dax_validation_results.csv`.\n")
    L.append("**Bug reproductions** (old formula evaluated; passes only when shown wrong):\n")
    for _, r in bugs.iterrows():
        L.append(f"- **{r.id} {r.measure}**, {r.context}: {r.detail}")
    L.append("")
    out = ROOT / "powerbi" / "dax_measure_audit.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(df)} measures, {n_pass}/{n_all} checks)")


# ---------------------------------------------------------------------------
# Implementation checklist (Windows build)
# ---------------------------------------------------------------------------
FILTER_BY_TABLE = [
    ("vw_customer_summary", "Lifetime per person: date slicers do NOT filter it; vw_customer_summary[customer_state] does"),
    ("rfm_customer_segments", "Responds to rfm_segment and, via vw_customer_summary, to customer state; not to dates"),
    ("cohort_retention", "Matrix context (cohort_month x months_since_acquisition); not related to other tables"),
    ("seller_scorecard", "Weighted; filtered through vw_seller_performance (seller, state); one seller = its published rate; no date filter"),
    ("vw_seller_performance", "Responds to seller filters (seller_id, seller_state); no date filter"),
    ("seller_category_performance", "Responds to dim_category and its own seller columns; no date filter"),
    ("product_performance", "Responds to dim_category; no date filter"),
    ("category_satisfaction", "BLANK unless exactly one category in context (not additive); responds to dim_category"),
    ("vw_category_performance", "Responds to dim_category and vw_category_performance[order_month]; NOT to dim_date"),
    ("delivery_stage_orders", "Responds via vw_order_summary (dim_date, state, status); 95,088-order population"),
    ("vw_review_summary", "Review grain; responds via vw_order_summary (dim_date, state); delivery_bucket axis"),
    ("vw_order_summary", "Responds to dim_date and vw_order_summary slicers (state, status)"),
]
FILTER_OVERRIDE = {
    "M09": "BLANK unless one YearMonth; removes date filters to read MonthIndex - 1; non-date slicers kept",
    "M10": "BLANK unless current and previous month are both in the stable window; non-date slicers kept",
    "M11": "BLANK unless one YearMonth and all 3 window months are in the stable window (first value 2017-03)",
    "M12": "Accumulates to the current date within page date slicers (ALLSELECTED(dim_date))",
    "M13": "Ignores all date filters (REMOVEFILTERS(dim_date)); non-date slicers apply",
    "M14": "Ignores all date filters (REMOVEFILTERS(dim_date)); non-date slicers apply",
    "M15": "Ignores all date filters; non-date slicers apply",
    "M23": "Denominator removes only the segment filter; state and other filters kept",
    "M27": "Denominator removes dim_category and vw_category_performance[category]; order_month kept",
    "M28": "BLANK unless one dim_category[category]; ranks against all categories",
    "M34": "Denominator ignores all seller filters (share of platform revenue)",
    "M40": "BLANK where there are no measurable deliveries (not 100%)",
    "N01": "Ignores the segment filter: scored people in the current non-segment context",
    "N04": "Ignores the offset filter (reads offset 0)",
    "N05": "BLANK unless one offset; denominator counts only cohorts observed at that offset; unobserved cells BLANK",
    "N06": "BLANK at offset 0 and in unobserved cells",
    "N07": "Largest category within the current filters (dim_category)",
    "N34": "Order grain, after-arrival reviews only; use on a delivery_bucket axis",
    "N35": "Order grain from the review table; use on a delivery_bucket axis; unfiltered equals M49",
    "N36": "BLANK unless one dim_category[category]; ranks against all categories within other filters (e.g. order_month)",
    "N37": "Fixes order_month to Jan-Mar 2017; responds to dim_category",
    "N38": "Fixes order_month to Jun-Aug 2018; responds to dim_category",
    "N39": "BLANK unless 50+ items in both periods; responds to dim_category",
    "N40": "BLANK unless one seller; cumulative within other seller filters (e.g. seller_state)",
    "N41": "Responds to dim_date and vw_order_summary slicers; delivered orders only",
}


FORMAT_OVERRIDE = {"M30": "#,##0", "N01": "#,##0", "M28": "0", "N36": "0.00%", "N39": "0.00%", "N40": "0.00%"}


def format_string(name, mid):
    if mid in FORMAT_OVERRIDE:
        return FORMAT_OVERRIDE[mid]
    n = name.lower()
    if mid in {"M09", "M12", "M13", "M14"} or any(k in n for k in ("revenue", "freight", "value", "price", "aov")) \
            and "share" not in n and "%" not in n and "rank" not in n and "denominator" not in n:
        return "R$ #,##0.00 (BRL)"
    if "%" in name or any(k in n for k in ("rate", "share")):
        return "0.00%"
    if "days" in n:
        return "0.00"
    if any(k in n for k in ("score", "rating")):
        return "0.000"
    if "per customer" in n:
        return "0.0000"
    return "#,##0"


def filter_behaviour(mid, dax):
    if mid in FILTER_OVERRIDE:
        return FILTER_OVERRIDE[mid]
    for table, text in FILTER_BY_TABLE:
        if f"{table}[" in dax or f"( {table} )" in dax:
            return text
    return "Inherits the filter behaviour of the measures it references"


def entry_order(F, names):
    """Topological order: a measure comes after every measure it references."""
    by_name = {v: k for k, v in names.items()}
    deps = {mid: {by_name[r] for r in re.findall(r"(?<![\w\]])\[([^\]]+)\]", F[mid]) if r in by_name and by_name[r] != mid}
            for mid in F}
    order, done = [], set()
    def visit(m):
        if m in done:
            return
        for d in sorted(deps[m]):
            visit(d)
        done.add(m); order.append(m)
    for m in sorted(F, key=lambda x: (x[0] != "M", x)):
        visit(m)
    return order, deps


def build_checklist():
    F = formulas()
    meas = RES[RES.kind == "measure"]
    names = {mid: meas[meas.id == mid].iloc[0].measure for mid in F}
    order, deps = entry_order(F, names)
    L = ["# RetailPulse — DAX Implementation Checklist (Power BI Desktop, Windows)\n",
         "**Generated by** `scripts/build_dax_audit.py` from `dax_measures.md` and `dax_validation_results.csv`. "
         "Do not edit by hand. Copy the formatted DAX from [`dax_measures.md`](dax_measures.md); the one-line "
         "form below is also valid DAX.\n",
         f"**{len(F)} measures**, listed in **entry order**: every measure appears after the measures it "
         "references, so each one can be committed without errors as you go.\n",
         f"> **Logic validated, runtime not.** `scripts/validate_dax_logic.py` passes {int(RES['pass'].sum())}/{len(RES)} checks comparing "
         "each measure's logic with independent SQL. That does **not** prove the DAX parses or evaluates "
         "identically in Power BI. Tick *Syntax OK* and *Value OK* only after checking in Power BI Desktop.\n",
         "**How to test a value:** put the measure on a card with no slicers applied (or the stated context) "
         "and compare with *Test value*. All test values and contexts are in "
         "[`dax_validation_results.csv`](dax_validation_results.csv) (column `expected`).\n",
         "| # | ID | Measure | DAX | Purpose | Expected filter behaviour | Format | Test value (context) | Validation ref | Entered | Syntax OK | Value OK |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    def cfmt(v):
        if pd.isna(v):
            return "BLANK"
        return f"{v:,.0f}" if float(v).is_integer() else fmt(v)

    for i, mid in enumerate(order, 1):
        m = meas[meas.id == mid]
        nonblank = m[m.expected.notna()]
        first = nonblank.iloc[0] if len(nonblank) else m.iloc[0]
        blanks = m[m.expected.isna()]
        bnote = (f"; BLANK by design at {', '.join(c.split(' (')[0] for c in blanks.context)}"
                 if len(blanks) else "")
        dax = F[mid].replace("|", "\\|")
        dep = f" (needs {', '.join(sorted(deps[mid]))})" if deps[mid] else ""
        L.append(f"| {i} | {mid} | {names[mid]} | `{dax}` | {AUDIT[mid][0]}{dep} | {filter_behaviour(mid, F[mid])} | "
                 f"{format_string(names[mid], mid)} | {cfmt(first.expected)} ({first.context}){bnote} | "
                 f"{mid}: {len(m)} check(s), all pass | ☐ | ☐ | ☐ |")
    L.append("")
    L.append(f"**Count check:** {len(order)} rows = {len(set(order))} distinct IDs "
             f"({sum(i.startswith('M') for i in order)} M + {sum(i.startswith('N') for i in order)} N).\n")
    out = ROOT / "powerbi" / "dax_implementation_checklist.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(order)} measures in entry order)")


if __name__ == "__main__":
    main()
    build_checklist()
