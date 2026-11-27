"""
RetailPulse - Tableau calculated fields: definitions, emulation and validation.

This script is the single source of truth for the Tableau Public dashboard. It
holds every calculated field (the 90 approved measures M01-M49 and N01-N41, ten
helper fields and two parameters), emulates how Tableau evaluates each one over
the CSVs in tableau/data/, and checks the result against independent SQL.

WHAT IS EMULATED (Tableau semantics)
  * Relationships: a filter on one logical table restricts the rows of the
    tables related to it; each measure is aggregated at its own table's grain
    (no fan-out).
  * Row-level IF inside an aggregate: IF ... THEN x END gives NULL otherwise;
    SUM / AVG / MEDIAN ignore NULL; COUNT counts non-NULL; COUNTD counts distinct
    non-NULL values and returns 0 (not NULL) when there are none.
  * Divisions are written as IF den > 0 THEN num / den END, which returns NULL
    (blank) instead of an error or 0 where there is nothing to divide by.
  * LOD expressions: FIXED is computed before dimension filters (ignores them);
    INCLUDE is computed after dimension filters, then re-aggregated.
  * Table calculations: LOOKUP, WINDOW_SUM, RUNNING_SUM, TOTAL, RANK_DENSE,
    computed along the stated "Compute Using" dimension over the marks that
    exist in the view, and table-calculation filters (applied last).

EXPECTED VALUES
  scripts/sql_reference.py answers each measure's business question in SQL on
  the BASE tables (never the views or the CSVs) in 223 filter contexts; the
  Tableau emulation is evaluated in the same contexts and compared. The
  drill-through, dashboard and fan-out checks also use SQL run here.

WHAT THIS CANNOT PROVE
  * that Tableau accepts the formula syntax, or that Tableau's engine evaluates
    it exactly as emulated (needs Tableau Desktop Public Edition: runtime test pending)
  * that the user builds the sheets, filters, actions and "Compute Using"
    settings as specified
  * formatting and layout

OUTPUTS
  tableau/tableau_calc_validation_results.csv   one row per check
  tableau/calculated_fields.md                  generated with --write-docs; without
                                                the flag the file is compared with
                                                what would be generated (drift check)

Read-only: the MySQL session is READ ONLY (app account from .env). No data changes.

Usage:
  ./venv/bin/python scripts/validate_tableau_calcs.py
  ./venv/bin/python scripts/validate_tableau_calcs.py --write-docs
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rp_db import ConfigError, get_connection                 # noqa: E402
import sql_reference                                          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser(description="Validate the Tableau calculated fields")
ap.add_argument("--write-docs", action="store_true", help="regenerate tableau/calculated_fields.md")
ARGS = ap.parse_args()

from tableau_registry import (A, BRL, CALC_BY_NAME, CALCS, D, DATA_SOURCES, DAYS, DEC2, FIELDS,  # noqa: E402,F401
                              HEADERS, INT, PARAMETERS, PCT, RENAMES, TAB)

DOC_PATH = TAB / "calculated_fields.md"
RESULTS_CSV = TAB / "tableau_calc_validation_results.csv"

# =============================================================================
# 3. DATA (exactly the CSVs Tableau connects to)
# =============================================================================
O = pd.read_csv(D / "vw_order_summary.csv", parse_dates=["order_date"], low_memory=False)
O["_ym"] = O.order_date.dt.strftime("%Y-%m")                  # = DATETRUNC('month', [order_date])
REV = pd.read_csv(D / "vw_review_summary.csv", low_memory=False)
DSO = pd.read_csv(A / "delivery_stage_orders.csv")
C = pd.read_csv(D / "vw_customer_summary.csv", low_memory=False)
RFM = pd.read_csv(A / "rfm_customer_segments.csv")
COH = pd.read_csv(A / "cohort_retention.csv")
DC = pd.read_csv(A / "dim_category.csv")
CAT = pd.read_csv(D / "vw_category_performance.csv")
PROD = pd.read_csv(A / "product_performance.csv")
CS = pd.read_csv(A / "category_satisfaction.csv")
SEL = pd.read_csv(D / "vw_seller_performance.csv")
SK = pd.read_csv(A / "seller_scorecard.csv")
SC = pd.read_csv(A / "seller_category_performance.csv")

try:
    CONN = get_connection(read_only=True)
except ConfigError as e:
    sys.exit(f"CONFIG ERROR: {e}")


def sql(query, params=None):
    cur = CONN.cursor(); cur.execute(query, params or ())
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=cols, dtype=object); cur.close()
    for c in df.columns:
        try:
            df[c] = pd.to_numeric(df[c])
        except (ValueError, TypeError):
            pass
    return df


def sv(query, params=None):
    v = sql(query, params).iloc[0, 0]
    return None if pd.isna(v) else float(v)


# ---- Tableau aggregate primitives ---------------------------------------------
def SUM(s):
    s = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    return None if s.empty else float(s.sum())


def AVG(s):
    s = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    return None if s.empty else float(s.mean())


def MEDIAN(s):
    s = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    return None if s.empty else float(s.median())


def COUNTD(s):
    return float(pd.Series(s).dropna().nunique())             # 0 when nothing is left (not NULL)


def COUNT(s):
    return float(pd.Series(s).notna().sum())


def IF(cond, val):
    """Row-level IF cond THEN val END: NULL where the condition is false."""
    return val.where(cond)


def guard(num, den):
    """IF den > 0 THEN num / den END (Tableau NULL arithmetic: anything with NULL is NULL)."""
    if den is None or den <= 0 or num is None:
        return None
    return num / den


def sub(a, b):
    return None if a is None or b is None else a - b


# =============================================================================
# 4. CONTEXT PARSING (the filter contexts of the SQL reference checks)
# =============================================================================
def parse(context):
    f = {}
    pats = {"month": r"(?<!order_)month = (\d{4}-\d{2})", "order_month": r"order_month = (\d{4}-\d{2})",
            "state": r"customer_state = ([A-Z]{2})", "seller_state": r"seller_state = ([A-Z]{2})",
            "status": r"order_status = (\w+)", "category": r"(?<![\w])category = ([a-z_0-9]+)",
            "segment": r"segment = (.+?)(?: within|$)", "bucket": r"delivery_bucket = (.+?)(?: \(|$)",
            "cohort": r"cohort ?= ?([\w-]+)", "offset": r"offset ?= ?(\w+)"}
    for k, p in pats.items():
        m = re.search(p, context)
        if m:
            f[k] = m.group(1).strip()
    if "Jan-Aug 2017" in context:
        f["janaug"] = 2017
    if "Jan-Aug 2018" in context:
        f["janaug"] = 2018
    if "largest seller" in context:
        f["seller"] = TOP_SELLER
    if "filter in_stable_window = 1" in context:
        f["stable"] = True
    return f


# ---- RP Orders ----------------------------------------------------------------------
def orders(f):
    o = O
    if f.get("month"):
        o = o[o._ym == f["month"]]
    if f.get("janaug"):
        o = o[(o.order_date.dt.year == f["janaug"]) & (o.order_date.dt.month <= 8)]
    if f.get("state"):
        o = o[o.customer_state == f["state"]]
    if f.get("status"):
        o = o[o.order_status == f["status"]]
    return o


def related(df, o, key="order_id"):
    """Relationship semantics: a filter on the parent restricts the related table's rows."""
    return df if len(o) == len(O) else df[df[key].isin(o[key])]


def reviews(f):
    r = related(REV, orders(f))
    if f.get("bucket"):
        r = r[r.delivery_bucket == f["bucket"]]
    return r


t_rev = lambda o: SUM(IF(o.revenue_eligible == 1, o.order_revenue))
t_aov_den = lambda o: COUNTD(IF((o.revenue_eligible == 1) & (o.item_count > 0), o.order_id))
t_meas = lambda o: COUNTD(IF(o.delivery_measurable == 1, o.order_id))
t_late = lambda o: SUM(IF(o.delivery_measurable == 1, o.is_late))


def month_view(o):
    marks = sorted(o._ym.unique())
    g = {m: s for m, s in o.groupby("_ym")}
    return marks, {m: t_rev(g[m]) for m in marks}, {m: float(g[m].in_stable_window.min()) for m in marks}


MV_ALL, MV_STABLE = month_view(O), month_view(O[O.in_stable_window == 1])
gap = lambda a, b: (pd.Period(b, "M") - pd.Period(a, "M")).n


def t_pm(m, mv=MV_ALL, guarded=True):
    marks, rev, _ = mv
    i = marks.index(m)
    if i < 1 or (guarded and gap(marks[i - 1], m) != 1):
        return None
    return rev[marks[i - 1]]


def t_mom(m, mv=MV_ALL):
    marks, rev, stab = mv
    i = marks.index(m)
    if i < 1:
        return None
    p = marks[i - 1]
    if not (stab[m] == 1 and stab[p] == 1 and gap(p, m) == 1) or rev[p] is None or rev[p] <= 0:
        return None
    return None if rev[m] is None else (rev[m] - rev[p]) / rev[p]


def t_ma3(m, mv=MV_ALL):
    marks, rev, stab = mv
    i = marks.index(m)
    if i < 2 or not (stab[m] == 1 and stab[marks[i - 2]] == 1 and gap(marks[i - 2], m) == 2):
        return None
    vals = [rev[x] for x in marks[i - 2:i + 1] if rev[x] is not None]
    return sum(vals) / 3 if vals else None


def t_running(m, stable):
    marks, rev, _ = MV_STABLE if stable else MV_ALL
    vals = [rev[x] for x in marks[:marks.index(m) + 1] if rev[x] is not None]
    return sum(vals) if vals else None


def t_janaug(year, f):
    o = orders({"state": f.get("state")})                    # sheet excluded from date filters
    return SUM(IF((o.order_date.dt.year == year) & (o.order_date.dt.month <= 8) & (o.revenue_eligible == 1),
                  o.order_revenue))


def t_order_rating_include(r, after_only=False):
    vals = r.review_score.where(r.review_before_delivery == 0) if after_only else r.review_score
    per_order = vals.groupby(r.order_id).mean()               # {INCLUDE [order_id] : AVG(...)}
    return AVG(per_order)


def stages(f):
    return related(DSO, orders(f))


def stage_days(f, col):
    s = stages(f)
    n = COUNT(s.total_seconds)
    return guard(SUM(s[col]), n * 86400 if n else 0)


def stage_share(f, col):
    s = stages(f)
    return guard(SUM(s[col]), SUM(s.total_seconds))


# ---- RP Customers ----------------------------------------------------------------
def customers(f):
    return C[C.customer_state == f["state"]] if f.get("state") else C


def rfm_view(f):
    v = RFM[RFM.rfm_scored == 1]                              # sheet filter: rfm_scored = 1
    if f.get("state"):
        v = v[v.customer_unique_id.isin(customers(f).customer_unique_id)]
    return v


def rfm_measure(mid, f):
    v = rfm_view(f)
    seg = v[v.rfm_segment == f["segment"]] if f.get("segment") else v
    total_scored = SUM(v.rfm_scored)                          # TOTAL(SUM([rfm_scored]))
    in_seg = SUM(seg.rfm_scored)
    if mid == "N01":
        return total_scored
    if mid == "M22":
        return in_seg
    if mid == "M23":
        return guard(SUM(seg.monetary_value), SUM(v.monetary_value))
    if mid == "N02":
        return guard(in_seg, total_scored)
    if mid == "N03":
        return guard(SUM(IF(seg.rfm_scored == 1, seg.monetary_value)), in_seg)


# ---- RP Cohorts --------------------------------------------------------------------
def cohort_cell(f):
    c = COH
    if f.get("cohort") and f["cohort"] != "all":
        c = c[c.cohort_month == f["cohort"]]
    if f.get("offset") and f["offset"] != "all":
        c = c[c.months_since_acquisition == int(f["offset"])]
    return c


def t_retention(c):
    if c.months_since_acquisition.min() != c.months_since_acquisition.max():
        return None
    return guard(SUM(c.active_customers), SUM(IF(c.is_observed == 1, c.cohort_customers)))


# ---- RP Categories ---------------------------------------------------------------
def cat_rows(f):
    c = CAT
    if f.get("category"):
        c = c[c.category == f["category"]]
    if f.get("order_month"):
        c = c[c.order_month == f["order_month"]]
    return c


Q1 = ("2017-01", "2017-03")
JA = ("2018-06", "2018-08")
in_rng = lambda s, r: (s >= r[0]) & (s <= r[1])


def t_growth(c):
    rows = CAT[CAT.category == c] if c else CAT
    i1 = SUM(IF(in_rng(rows.order_month, Q1), rows.items_sold))
    i2 = SUM(IF(in_rng(rows.order_month, JA), rows.items_sold))
    r1 = SUM(IF(in_rng(rows.order_month, Q1), rows.revenue))
    r2 = SUM(IF(in_rng(rows.order_month, JA), rows.revenue))
    if i1 is None or i2 is None or i1 < 50 or i2 < 50 or r1 is None or r1 <= 0:
        return None
    return sub(r2, r1) / r1


CAT_VIEW = CAT.groupby("category").revenue.sum().reindex(DC.category)            # one mark per category
CAT_SORTED = CAT_VIEW.sort_values(ascending=False, kind="mergesort")
T_CAT_RANK = CAT_VIEW.rank(method="dense", ascending=False)                       # RANK_DENSE(..., 'desc')
T_CAT_CUM = CAT_SORTED.cumsum() / CAT_SORTED.sum()                                # RUNNING_SUM / TOTAL


def prod_rows(f):
    return PROD[PROD.category == f["category"]] if f.get("category") else PROD


def cs_value(f, col, scale=1.0):
    rows = CS[CS.category == f["category"]] if f.get("category") else CS
    if COUNTD(rows.category) != 1:
        return None
    v = SUM(rows[col])
    return None if v is None else v / scale


# ---- RP Sellers ------------------------------------------------------------------
def seller_rows(f):
    s, scp = SEL, SC
    if f.get("seller_state"):
        s = s[s.seller_state == f["seller_state"]]
    if f.get("seller"):
        s = s[s.seller_id == f["seller"]]
    if f.get("category"):                                     # filter on a seller_category_performance field
        scp = scp[scp.category == f["category"]]
        s = s[s.seller_id.isin(scp.seller_id)]
    scp = scp[scp.seller_id.isin(s.seller_id)]
    return s, SK[SK.seller_id.isin(s.seller_id)], scp


SEL_SORTED = SEL.set_index("seller_id").revenue.sort_values(ascending=False, kind="mergesort")
T_SEL_CUM = SEL_SORTED.cumsum() / SEL_SORTED.sum()

# =============================================================================
# 5. SQL REFERENCES computed here (independent of the exported CSVs)
# =============================================================================
E_CAT = sql("""SELECT p.product_category_name_english cat, SUM(oi.price) rev,
                      SUM(DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') BETWEEN '2017-01' AND '2017-03') i1,
                      SUM(DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') BETWEEN '2018-06' AND '2018-08') i2,
                      SUM(CASE WHEN DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') BETWEEN '2017-01' AND '2017-03'
                               THEN oi.price ELSE 0 END) r1,
                      SUM(CASE WHEN DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') BETWEEN '2018-06' AND '2018-08'
                               THEN oi.price ELSE 0 END) r2
               FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
               JOIN products p ON p.product_id = oi.product_id
               WHERE o.revenue_eligible = 1 GROUP BY cat""").set_index("cat")
E_CAT_RANK = E_CAT.rev.rank(method="dense", ascending=False)
E_CAT_CUM = E_CAT.rev.map(lambda v: E_CAT.rev[E_CAT.rev >= v].sum()) / E_CAT.rev.sum()     # ">=" definition
E_GROWTH = pd.Series(np.where((E_CAT.i1 >= 50) & (E_CAT.i2 >= 50), (E_CAT.r2 - E_CAT.r1) / E_CAT.r1.replace(0, np.nan),
                              np.nan), index=E_CAT.index)
E_SELLER = sql("""WITH p AS (SELECT DISTINCT oi.seller_id, oi.order_id FROM order_items oi
                             JOIN orders o ON o.order_id = oi.order_id WHERE o.revenue_eligible = 1),
                       sc AS (SELECT order_id, SUM(review_score) / (COUNT(*) * 1e0) s FROM order_reviews GROUP BY order_id),
                       r AS (SELECT oi.seller_id, SUM(oi.price) rev FROM order_items oi
                             JOIN orders o ON o.order_id = oi.order_id WHERE o.revenue_eligible = 1 GROUP BY oi.seller_id)
                  SELECT p.seller_id, COUNT(*) pairs, AVG(sc.s) rating, MAX(r.rev) rev
                  FROM p LEFT JOIN sc ON sc.order_id = p.order_id JOIN r ON r.seller_id = p.seller_id
                  GROUP BY p.seller_id""").set_index("seller_id")
E_SELLER = E_SELLER.sort_values("rev", ascending=False, kind="mergesort")
E_SEL_CUM = E_SELLER.rev.map(lambda v: E_SELLER.rev[E_SELLER.rev >= v].sum()) / E_SELLER.rev.sum()
TOP_SELLER = E_SELLER.index[0]

# =============================================================================
# 6. CHECKS
# =============================================================================
RESULTS: list[dict] = []
MONEY = 0.005


REF = pd.DataFrame(sql_reference.build(sql, sv))         # SQL on the base tables, 223 contexts


def record(cid, name, context, kind, value, expected, tol, note="", ok=None):
    if ok is None:
        if value is None or expected is None:
            ok = value is None and expected is None
        else:
            ok = abs(value - expected) <= tol
    RESULTS.append({"id": cid, "calculated_field": name, "context": context, "kind": kind,
                    "tableau": value, "expected": expected, "pass": bool(ok), "note": note})


def nz(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)


# ---- 6a. every SQL reference check, in Tableau semantics ------------------------------
def emulate(mid, context):
    """Tableau formula for measure `mid`, evaluated in the reference check's filter context.
    Returns (value, expected_override, note)."""
    f = parse(context)
    o = orders(f)
    page_slicer = "dashboard date filter" in context
    single = {
        "M01": lambda: t_rev(o), "M02": lambda: COUNTD(o.order_id), "M03": lambda: COUNTD(o.customer_unique_id),
        "M04": lambda: COUNTD(IF(o.item_count > 0, o.order_id)), "M05": lambda: t_aov_den(o),
        "M06": lambda: guard(t_rev(o), t_aov_den(o)),
        "M07": lambda: MEDIAN(IF((o.revenue_eligible == 1) & (o.item_count > 0), o.order_revenue)),
        "M08": lambda: SUM(IF(o.revenue_eligible == 1, o.order_freight)),
        "M09": lambda: t_pm(f["month"]), "M10": lambda: t_mom(f["month"]), "M11": lambda: t_ma3(f["month"]),
        "M12": lambda: t_running(f["month"], f.get("stable", False)),
        "M13": lambda: t_janaug(2017, f), "M14": lambda: t_janaug(2018, f),
        "M15": lambda: guard(sub(t_janaug(2018, f), t_janaug(2017, f)), t_janaug(2017, f)),
        "M16": lambda: COUNTD(customers(f).customer_unique_id),
        "M17": lambda: COUNTD(IF(customers(f).total_orders >= 2, customers(f).customer_unique_id)),
        "M18": lambda: COUNTD(IF(customers(f).total_orders == 1, customers(f).customer_unique_id)),
        "M19": lambda: guard(COUNTD(IF(customers(f).total_orders >= 2, customers(f).customer_unique_id)),
                             COUNTD(customers(f).customer_unique_id)),
        "M20": lambda: AVG(customers(f).total_orders), "M21": lambda: SUM(customers(f).historical_value),
        "N04": lambda: SUM(IF(cohort_cell(f).months_since_acquisition == 0, cohort_cell(f).cohort_customers)),
        "N05": lambda: t_retention(cohort_cell(f)), "N06": lambda: SUM(cohort_cell(f).returning_customers),
        "M24": lambda: SUM(cat_rows(f).revenue), "M25": lambda: SUM(cat_rows(f).items_sold),
        "M26": lambda: COUNTD(cat_rows(f).category),
        "M27": lambda: guard(SUM(cat_rows(f).revenue), SUM(CAT.revenue)),          # FIXED total ignores filters
        "N07": lambda: float(cat_rows(f).groupby("category").revenue.sum().max()),
        "N37": lambda: SUM(IF(in_rng(cat_rows(f).order_month, Q1), cat_rows(f).revenue)),
        "N38": lambda: SUM(IF(in_rng(cat_rows(f).order_month, JA), cat_rows(f).revenue)),
        "N08": lambda: SUM(prod_rows(f).product_revenue), "N09": lambda: SUM(prod_rows(f).units_sold),
        "N10": lambda: COUNTD(IF(prod_rows(f).units_sold > 0, prod_rows(f).product_id)),
        "N11": lambda: guard(SUM(prod_rows(f).product_revenue), SUM(prod_rows(f).units_sold)),
        "N12": lambda: guard(SUM(prod_rows(f).freight_value), SUM(prod_rows(f).units_sold)),
        "N29": lambda: cs_value(f, "review_count"), "N30": lambda: cs_value(f, "avg_review_score"),
        "N31": lambda: cs_value(f, "one_star_pct", 100), "N32": lambda: cs_value(f, "avg_review_score_after_arrival"),
        "N33": lambda: cs_value(f, "pct_reviews_before_delivery", 100),
        "M29": lambda: SUM(seller_rows(f)[0].revenue), "M30": lambda: COUNTD(seller_rows(f)[0].seller_id),
        "M31": lambda: SUM(seller_rows(f)[0].orders_served),
        "M32": lambda: guard(SUM(seller_rows(f)[1].delivery_days_sum), SUM(seller_rows(f)[1].delivery_measurable_orders)),
        "M33": lambda: guard(SUM(seller_rows(f)[1].late_orders), SUM(seller_rows(f)[1].delivery_measurable_orders)),
        "M35": lambda: guard(SUM(seller_rows(f)[1].review_score_sum), SUM(seller_rows(f)[1].reviewed_orders)),
        "M34": lambda: guard(float(seller_rows(f)[0].groupby("seller_id").revenue.sum().max()), SUM(SEL.revenue)),
        "N13": lambda: SUM(seller_rows(f)[2].product_revenue), "N14": lambda: SUM(seller_rows(f)[2].item_count),
        "N15": lambda: guard(SUM(seller_rows(f)[2].late_orders), SUM(seller_rows(f)[2].delivery_measurable_orders)),
        "N16": lambda: guard(SUM(seller_rows(f)[2].dispatch_measurable_orders * seller_rows(f)[2].avg_dispatch_days),
                             SUM(seller_rows(f)[2].dispatch_measurable_orders)),
        "M36": lambda: COUNTD(IF(o.is_delivered == 1, o.order_id)), "M37": lambda: t_meas(o), "M38": lambda: t_late(o),
        "M39": lambda: guard(t_late(o), t_meas(o)), "M40": lambda: guard(sub(t_meas(o), t_late(o)), t_meas(o)),
        "M41": lambda: AVG(IF(o.delivery_measurable == 1, o.delivery_days)),
        "M42": lambda: AVG(IF(o.delivery_measurable == 1, o.delay_days)),
        "N41": lambda: AVG(IF(o.delivery_measurable == 1, o.delivery_days - o.delay_days)),
        "M43": lambda: COUNTD(IF(o.order_status == "canceled", o.order_id)),
        "M44": lambda: guard(COUNTD(IF(o.order_status == "canceled", o.order_id)), COUNTD(o.order_id)),
        "N17": lambda: COUNT(stages(f).total_seconds),
        "N18": lambda: stage_days(f, "purchase_to_approval_seconds"),
        "N19": lambda: stage_days(f, "approval_to_carrier_seconds"),
        "N20": lambda: stage_days(f, "carrier_to_customer_seconds"),
        "N21": lambda: stage_days(f, "total_seconds"),
        "N22": lambda: stage_share(f, "carrier_to_customer_seconds"),
        "N23": lambda: stage_share(f, "approval_to_carrier_seconds"),
        "N24": lambda: stage_share(f, "purchase_to_approval_seconds"),
        "M45": lambda: COUNT(reviews(f).review_id), "M46": lambda: AVG(reviews(f).review_score),
        "M47": lambda: guard(COUNT(IF(reviews(f).review_score == 1, reviews(f).review_id)), COUNT(reviews(f).review_id)),
        "M48": lambda: guard(COUNT(IF(reviews(f).review_score == 5, reviews(f).review_id)), COUNT(reviews(f).review_id)),
        "M49": lambda: AVG(IF(o.review_count > 0, o.review_score_avg)),
        "N25": lambda: COUNT(IF(reviews(f).review_before_delivery == 1, reviews(f).review_id)),
        "N26": lambda: guard(COUNT(IF(reviews(f).review_before_delivery == 1, reviews(f).review_id)),
                             COUNT(IF(reviews(f).review_before_delivery.notna(), reviews(f).review_id))),
        "N27": lambda: AVG(IF(reviews(f).review_before_delivery == 0, reviews(f).review_score)),
        "N28": lambda: guard(COUNT(IF((reviews(f).review_before_delivery == 0) & (reviews(f).review_score == 1),
                                      reviews(f).review_id)),
                             COUNT(IF(reviews(f).review_before_delivery == 0, reviews(f).review_id))),
        "N35": lambda: t_order_rating_include(reviews(f)),
        "N34": lambda: t_order_rating_include(reviews(f), after_only=True),
    }
    note = "YoY sheets must be excluded from the date filters" if page_slicer else ""
    if mid in ("N01", "M22", "M23", "N02", "N03"):
        return rfm_measure(mid, f), None, note
    if mid == "M28":
        n = sum(T_CAT_RANK[c] == E_CAT_RANK.get(c) for c in DC.category)
        return float(n), None, "RANK_DENSE over all 74 category marks vs SQL dense rank"
    if mid == "N36":
        if "reach 80%" in context:
            return float((T_CAT_CUM < 0.8).sum() + 1), None, "position where RUNNING_SUM share first reaches 80%"
        if "74 in one" in context:
            n = sum(abs(T_CAT_CUM[c] - E_CAT_CUM[c]) < 1e-9 for c in DC.category)
            return float(n), None, "every category vs SQL cumulative share"
        return float(T_CAT_CUM[f["category"]]), None, ""
    if mid == "N39":
        if "grew" in context:
            return float(sum((t_growth(c) or 0) > 0 for c in DC.category)), None, ""
        if "74 in one" in context:
            n = sum((t_growth(c) is None and pd.isna(E_GROWTH.get(c))) or
                    (t_growth(c) is not None and abs(t_growth(c) - E_GROWTH[c]) < 1e-9) for c in DC.category)
            return float(n), None, "every category vs SQL growth"
        return t_growth(f["category"]), None, ""
    if mid == "N40":
        m = re.search(r"seller ranked (\d+)", context)
        if m:
            sid = E_SELLER.index[int(m.group(1)) - 1]
            return float(T_SEL_CUM[sid]), None, ""
        exact = sum(abs(T_SEL_CUM[s] - E_SEL_CUM[s]) < 1e-9 for s in E_SELLER.index)
        return float(exact), None, "count of sellers whose RUNNING_SUM share equals the '>=' definition"
    if mid == "N05" and f.get("cohort") == "all" and f.get("offset") == "all":
        return t_retention(COH), None, ""
    return single[mid](), None, note


for _, row in REF.iterrows():
    nm = row.measure
    try:
        val, override, note = emulate(row.id, row.context)
        val = nz(val)
        expected = nz(row.expected) if override is None else override
        note = "; ".join(x for x in (row.note, note) if x)
        record(row.id, nm, row.context, "reference check", val, expected, row.tol + 1e-12, note)
    except Exception as ex:                                  # noqa: BLE001
        record(row.id, nm, row.context, "reference check", None, nz(row.expected), 0,
               f"{type(ex).__name__}: {ex}", ok=False)

# ---- 6b. fan-out guards: revenue through every source equals SQL (no duplication) ---
BASE_TOTAL = sv("SELECT SUM(oi.price) FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
                "WHERE o.revenue_eligible = 1")
for nm, val in [("vw_order_summary (Total Revenue)", t_rev(O)), ("vw_category_performance (Category Revenue)", SUM(CAT.revenue)),
                ("vw_seller_performance (Seller Revenue)", SUM(SEL.revenue)),
                ("vw_customer_summary (Historical Customer Value)", SUM(C.historical_value)),
                ("product_performance (Product Revenue)", SUM(PROD.product_revenue)),
                ("seller_category_performance (Seller Category Revenue)", SUM(SC.product_revenue)),
                ("rfm_customer_segments (monetary_value)", SUM(RFM.monetary_value))]:
    record("X01", "Revenue reconciliation", f"total via {nm} = SQL item revenue", "fan-out guard", val, BASE_TOTAL, MONEY)

# ---- 6c. drill-through and dashboard checks (parameter + table-calculation filters) ----
hb = "health_beauty"
record("D01", "Category Rank", "Category Detail, p_category = health_beauty (TC filter H05)", "dashboard",
       float(T_CAT_RANK[hb]), float(E_CAT_RANK[hb]), 0)
record("D02", "Category Cumulative Share", "Category Detail, p_category = health_beauty (TC filter H05)",
       "dashboard", float(T_CAT_CUM[hb]), float(E_CAT_CUM[hb]), 1e-9)
f_hb = {"category": hb}
record("D03", "Category Revenue Share", "Category Detail, p_category = health_beauty (FIXED denominator)",
       "dashboard", guard(SUM(cat_rows(f_hb).revenue), SUM(CAT.revenue)), float(E_CAT.rev[hb] / E_CAT.rev.sum()), 1e-9)
record("D04", "Seller Cumulative Share", "Seller Detail, p_seller = largest seller (TC filter H07)", "dashboard",
       float(T_SEL_CUM[TOP_SELLER]), float(E_SEL_CUM[TOP_SELLER]), 1e-9)
fs = {"seller": TOP_SELLER}
e_cats = sv("SELECT COUNT(DISTINCT p.product_category_name_english) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id "
            "JOIN products p ON p.product_id = oi.product_id WHERE o.revenue_eligible = 1 AND oi.seller_id = %s", (TOP_SELLER,))
record("D05", "Categories sold (COUNTD category)", "Seller Detail, p_seller = largest seller", "dashboard",
       COUNTD(seller_rows(fs)[2].category), e_cats, 0)
record("D06", "Seller Category Revenue (sum of category rows)", "Seller Detail, p_seller = largest seller",
       "dashboard", SUM(seller_rows(fs)[2].product_revenue), float(E_SELLER.rev[TOP_SELLER]), MONEY)
record("D07", "Seller Orders", "Seller Detail, p_seller = largest seller", "dashboard",
       SUM(seller_rows(fs)[0].orders_served), float(E_SELLER.pairs[TOP_SELLER]), 0)
st = sql("SELECT c.customer_state st, SUM(oi.price) r FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
         "JOIN customers c ON c.customer_id = o.customer_id WHERE o.revenue_eligible = 1 GROUP BY st ORDER BY r DESC")
t_states = O[O.revenue_eligible == 1].groupby("customer_state").order_revenue.sum().sort_values(ascending=False)
record("D08", "Top-3 state revenue share (caption)", "Executive, revenue by state", "dashboard",
       float(t_states.head(3).sum() / t_states.sum()), float(st.r.head(3).sum() / st.r.sum()), 1e-9)
t_rating = (SK.set_index("seller_id").review_score_sum / SK.set_index("seller_id").reviewed_orders.replace(0, np.nan))
t_orders = SEL.set_index("seller_id").orders_served
record("D09", "Needs Intervention (row count)", "Sellers, intervention table", "dashboard",
       float(((t_orders >= 100) & (t_rating.reindex(t_orders.index) < 3.8)).sum()),
       float(((E_SELLER.pairs >= 100) & (E_SELLER.rating < 3.8)).sum()), 0)
record("D10", "Seller Has 50+ Orders (row count)", "Sellers, rankings and scatter", "dashboard",
       float((t_orders >= 50).sum()), float((E_SELLER.pairs >= 50).sum()), 0)

# ---- 6d. pitfalls: wrong Tableau formulations, shown to be wrong -----------------
ref_val = lambda mid, ctx: nz(REF[(REF.id == mid) & (REF.context == ctx)].expected.iloc[0])  # SQL reference


def pitfall(pid, name, context, demonstrated, detail):
    try:
        ok = bool(demonstrated())
    except Exception as ex:                                  # noqa: BLE001
        ok, detail = False, f"{type(ex).__name__}: {ex}"
    RESULTS.append({"id": pid, "calculated_field": name, "context": context, "kind": "pitfall shown wrong",
                    "tableau": None, "expected": None, "pass": ok, "note": detail})


naive_pm = t_pm("2016-12", guarded=False)
pitfall("P01", "Revenue PM", "LOOKUP(-1) without the DATEDIFF guard at 2016-12",
        lambda: naive_pm is not None and ref_val("M09", "month = 2016-12") is None,
        f"returns October 2016 revenue {naive_pm:,.2f}; correct value is BLANK (November 2016 has no orders)")
row_fixed = REV.groupby("order_id").review_score.transform("mean")
p02 = AVG(row_fixed)
pitfall("P02", "Avg Order Rating (Review Table)", "AVG over review rows of {FIXED [order_id]: AVG([review_score])}",
        lambda: abs(p02 - ref_val("N35", "unfiltered (must equal M49 at full precision)")) > 1e-6,
        f"gives {p02:.6f} (multi-review orders counted once per review) vs order-grain "
        f"{ref_val('N35', 'unfiltered (must equal M49 at full precision)'):.6f}")
p03 = COUNTD(REV.review_id)
pitfall("P03", "Total Reviews", "COUNTD([review_id]) instead of COUNT",
        lambda: p03 != ref_val("M45", "unfiltered"),
        f"COUNTD gives {p03:,.0f}; there are {ref_val('M45', 'unfiltered'):,.0f} reviews (814 rows repeat a review_id)")
top15 = CAT_SORTED.head(15)
p04 = float(CAT_VIEW[hb] / top15.sum())
pitfall("P04", "Category Revenue Share", "SUM/TOTAL(SUM) on a chart with a Top-15 filter",
        lambda: abs(p04 - ref_val("M27", "category = health_beauty")) > 1e-4,
        f"health_beauty would show {p04 * 100:.2f}% of the top 15 instead of "
        f"{ref_val('M27', 'category = health_beauty') * 100:.2f}% of all revenue")
joined = O.merge(REV[["order_id"]], on="order_id", how="inner")
p05 = t_rev(joined)
pitfall("P05", "Total Revenue", "physical JOIN of vw_order_summary and vw_review_summary instead of a relationship",
        lambda: p05 - ref_val("M01", "unfiltered") > 1000 or ref_val("M01", "unfiltered") - p05 > 1000,
        f"join gives {p05:,.2f} vs {ref_val('M01', 'unfiltered'):,.2f} (orders with 2-3 reviews repeat; "
        "orders without a review drop)")
b = "1-7 days late"
rb = REV[REV.delivery_bucket == b]
fixed_all = REV.groupby("order_id").review_score.mean()
p06 = AVG(fixed_all.reindex(rb[rb.review_before_delivery == 0].order_id.unique()))
pitfall("P06", "Avg Order Rating After Arrival", "FIXED order average + review_before_delivery = 0 as a normal filter",
        lambda: abs(p06 - ref_val("N34", f"delivery_bucket = {b}")) > 1e-4,
        f"gives {p06:.3f} for '{b}' (FIXED ignores the filter, so pre-arrival reviews leak in) vs "
        f"{ref_val('N34', f'delivery_bucket = {b}'):.3f}")
p07 = COUNTD(orders({"month": "2017-11"}).customer_unique_id)
pitfall("P07", "Total People", "customer table in the orders data source with an Order Month = 2017-11 filter",
        lambda: p07 != ref_val("M16", "unfiltered"),
        f"the relationship would cut lifetime people to {p07:,.0f} (those who ordered that month) instead of "
        f"{ref_val('M16', 'unfiltered'):,.0f}; hence a separate RP Customers data source")
diff = (T_SEL_CUM.reindex(E_SELLER.index) - E_SEL_CUM).abs()
first_diff = int(np.argmax(diff.values > 1e-9)) + 1
pitfall("P08", "Seller Cumulative Share", "RUNNING_SUM vs the '>=' definition on tied seller revenues (documented difference)",
        lambda: diff.max() < 5e-4 and first_diff > 306,
        f"{int((diff > 1e-9).sum())} sellers differ, max {diff.max() * 100:.4f} percentage points, first at position "
        f"{first_diff} (after the 306 sellers in the specification caption)")
m_jan = cat_rows({"category": hb, "order_month": "2018-01"}).revenue.sum()
p09 = float(m_jan / CAT.revenue.sum())
dax09 = float(m_jan / CAT[CAT.order_month == "2018-01"].revenue.sum())
pitfall("P09", "Category Revenue Share", "FIXED denominator with a NON-context month filter (order_month = 2018-01)",
        lambda: abs(p09 - dax09) > 1e-4,
        f"gives {p09 * 100:.3f}% (share of all-time revenue) vs {dax09 * 100:.3f}% within the month; add any month "
        "filter on these sheets to context")

CONN.close()

# ---- 6e. coverage and static checks ------------------------------------------------
APPROVED = {f"M{i:02d}" for i in range(1, 50)} | {f"N{i:02d}" for i in range(1, 42)}   # the 90 approved measures
ref_names = dict(zip(REF.id, REF.measure))
calc_ids = {c["id"]: c["name"] for c in CALCS if c["id"][0] in "MN"}
cov = [("every one of the 90 approved measures (M01-M49, N01-N41) has a calculated field", sorted(APPROVED - set(calc_ids))),
       ("no calculated field outside the approved measure list", sorted(set(calc_ids) - APPROVED)),
       ("every approved measure has SQL reference checks", sorted(APPROVED - set(ref_names))),
       ("field names equal the measure names used by the SQL reference", sorted(i for i in calc_ids if ref_names.get(i) != calc_ids[i])),
       ("every calculated field has a business definition and a note",
        sorted(c["id"] for c in CALCS if not c["definition"].strip() or not c["note"].strip()))]
checked_ids = {r["id"] for r in RESULTS if r["kind"] == "reference check" and r["pass"]}
cov.append(("every Tableau measure has at least one passing check", sorted(set(calc_ids) - checked_ids)))
for ds in DATA_SOURCES:
    names = set(FIELDS[ds]) | {c["name"] for c in CALCS if c["ds"] == ds} | set(PARAMETERS)
    bad = []
    for c in (c for c in CALCS if c["ds"] == ds):
        for tok in re.findall(r"\[([^\]]+)\]", c["formula"]):
            if tok not in names:
                bad.append(f"{c['id']}:[{tok}]")
    cov.append((f"{ds}: every [field] in every formula exists (after renames) or is a calc/parameter", bad))
# every name the dashboard specification puts in backticks is a real field, calculation,
# parameter, table, or one of the listed non-field items (sheet names, values, colours, files)
ALL_NAMES = set(PARAMETERS) | {c["name"] for c in CALCS} | set(HEADERS)
for ds in FIELDS:
    ALL_NAMES |= set(FIELDS[ds])
NON_FIELDS = {"Measure Names", "Measure Values", "R$ ", "health_beauty", "unavailable", "not delivered",
              "1.1 Revenue and Orders by Month", "7 Category Detail", "8 Seller Detail",
              "<dashboard>.0 KPIs", "<dashboard>.<n> <title>", "MIN(0)"}
spec_bad = []
for tok in sorted(set(re.findall(r"`([^`\n]+)`", (TAB / "dashboard_specification.md").read_text(encoding="utf-8")))):
    if tok in ALL_NAMES or tok in NON_FIELDS or tok.startswith("#") or re.search(r"\.(png|md|py|csv)$|/", tok):
        continue
    inner = re.fullmatch(r"(?:SUM|MIN|MAX|AVG|MEDIAN|YEAR|COUNT|COUNTD)\((.+)\)", tok)
    if inner:
        refs = re.findall(r"\[([^\]]+)\]", inner.group(1)) or [inner.group(1)]
        if all(r in ALL_NAMES for r in refs):
            continue
    spec_bad.append(tok)
cov.append(("every field/calculation named in dashboard_specification.md exists", spec_bad))
collisions = [f"{ds}:{new}" for ds, rs in RENAMES.items() for t, col, new in rs
              if any(new in HEADERS[tt] for tt, _, _, _ in DATA_SOURCES[ds])]
cov.append(("renamed fields do not collide with an existing column", collisions))
for label, bad in cov:
    RESULTS.append({"id": "COV", "calculated_field": "coverage", "context": label, "kind": "coverage / static",
                    "tableau": None, "expected": None, "pass": not bad, "note": ", ".join(bad[:10])})

# =============================================================================
# 7. DOCUMENTATION (generated) + drift check
# =============================================================================
res = pd.DataFrame(RESULTS)


def fmt_val(v, f):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "NULL (blank)"
    if f.startswith("R$"):
        return f"R$ {v:,.2f}"
    if f.startswith("Percentage"):
        return f"{v * 100:.2f}%"
    if f == INT:
        return f"{v:,.0f}"
    return f"{v:,.4f}"


def build_doc():
    out = []
    w = out.append
    w("# RetailPulse — Tableau Calculated Fields")
    w("")
    w("> **Generated file.** Do not edit by hand: it is written by "
      "`scripts/validate_tableau_calcs.py --write-docs` from the same registry the validator tests, so a "
      "formula and its test values cannot drift apart.")
    w("")
    n_m = sum(1 for c in CALCS if c["id"][0] in "MN")
    n_h = sum(1 for c in CALCS if c["id"][0] == "H")
    w(f"**{n_m} measures** (the approved catalogue M01–M49 and N01–N41) · **{n_h} helper fields** · "
      f"**{len(PARAMETERS)} parameters**. Data sources and relationships: [`data_model.md`](data_model.md). "
      "Step-by-step entry: [`mac_implementation_guide.md`](mac_implementation_guide.md).")
    w("")
    w("> **Already in the workbook.** Every field, parameter and rename below is written into the generated "
      "`tableau/RetailPulse.twb` by `scripts/build_tableau_workbook.py`, from the same registry "
      "(`scripts/tableau_registry.py`). You only type these formulas if you build the data sources by hand "
      "(guide §2–§6).")
    w("")
    w("## What \"validated\" means here")
    w("")
    w("| | |")
    w("|---|---|")
    w("| ✅ **Verified on macOS (Python + SQL)** | each formula's logic, emulated with Tableau's rules (relationships, "
      "NULL handling, FIXED/INCLUDE, table calculations, table-calculation filters) over the exact CSVs, matches "
      "an independent SQL answer on the base tables in every reference context (`scripts/sql_reference.py`) |")
    w("| ❌ **Not verified (pending Tableau runtime test)** | that Tableau accepts the syntax as typed; that Tableau's "
      "engine evaluates it exactly as emulated; your sheet, filter, \"Compute Using\" and action settings |")
    w("")
    w("Results: `tableau/tableau_calc_validation_results.csv` (one row per check). Re-run: "
      "`./venv/bin/python scripts/validate_tableau_calcs.py`.")
    w("")
    w("## How to read each entry")
    w("")
    w("- **Type**: *row-level* (computed per row), *aggregate* (computed per mark), *aggregate with LOD* "
      "(contains `{FIXED ...}` or `{INCLUDE ...}`), *table calculation* (computed across the marks of the view; "
      "set **Compute Using** exactly as stated: right-click the pill ▸ Compute Using).")
    w("- **Format**: set once on the field (Data pane ▸ right-click ▸ Default Properties ▸ Number Format). "
      "BRL: Currency (Custom), Decimal places 2, Prefix `R$ `.")
    w("- Field names are the CSV column names. Do the two naming steps in `mac_implementation_guide.md` §4 first "
      "(Reset name; rename duplicates) or the formulas will not find the fields.")
    w("- Every division is written `IF den > 0 THEN num / den END`: it returns NULL (blank) instead of an "
      "error or 0 where there is nothing to divide by.")
    w("- **Expected values** are the SQL reference values the formula reproduced; test the card against them in Tableau.")
    w("- **Revenue** everywhere is product revenue in BRL (item prices of revenue-eligible orders, freight excluded). "
      "It is not GMV (R$ 13,591,643.70, all statuses) and not profit (no cost data exists).")
    w("")
    w("## Parameters")
    w("")
    w("| Name | Data type | Current value | Allowable values | Purpose |")
    w("|---|---|---|---|---|")
    for p, (t, v, why) in PARAMETERS.items():
        w(f"| `{p}` | {t} | `{v}` | All | {why} |")
    w("")
    w("## Field renames (required before entering formulas)")
    w("")
    w("When two tables in one data source have a column with the same name, rename the later table's copy as "
      "below (Data Source page ▸ metadata grid ▸ find the row whose **Table** column matches ▸ click the field "
      "name ▸ Rename). Whatever label Tableau first shows for the duplicate, the final name must be exactly "
      "the **New name**.")
    w("")
    for ds, rs in RENAMES.items():
        if not rs:
            continue
        w(f"**{ds}**")
        w("")
        w("| Table | CSV column | New name |")
        w("|---|---|---|")
        for t, col, new in rs:
            w(f"| `{t}` | `{col}` | `{new}` |")
        w("")
    w("## Calculated fields by data source")
    w("")
    for ds in DATA_SOURCES:
        items = [c for c in CALCS if c["ds"] == ds]
        if not items:
            continue
        w(f"### {ds}")
        w("")
        w("| ID | Name | Type |")
        w("|---|---|---|")
        for c in items:
            w(f"| {c['id']} | {c['name']} | {c['kind']} |")
        w("")
        for c in items:
            w(f"#### {c['id']} · {c['name']}")
            w("")
            w(f"- **Definition:** {c['definition']}")
            w(f"- **Data source:** {ds} · **Type:** {c['kind']} · **Aggregation level / settings:** {c['level']}"
              + (f" · **Format:** {c['fmt']}" if c["fmt"] else ""))
            toks = sorted(set(re.findall(r"\[([^\]]+)\]", c["formula"])))
            srcs = [f"`{FIELDS[ds][t][0]}.{FIELDS[ds][t][1]}`" + (f" (as `{t}`)" if FIELDS[ds][t][1] != t else "")
                    for t in toks if t in FIELDS[ds]]
            deps = [f"`{t}`" for t in toks if t not in FIELDS[ds]]
            if srcs:
                w(f"- **Source fields:** {', '.join(srcs)}")
            if deps:
                w(f"- **Uses:** {', '.join(deps)}")
            w("")
            w("```")
            w(c["formula"])
            w("```")
            w("")
            w(f"- **Tableau notes:** {c['note']}")
            rows = res[(res.id == c["id"]) & (res.kind == "reference check")]
            if len(rows):
                vals = "; ".join(f"{r.context} → **{fmt_val(nz(r.tableau), c['fmt'])}**"
                                 + ("" if r["pass"] else " ❌") for _, r in rows.head(6).iterrows())
                more = f" (+{len(rows) - 6} more in the results CSV)" if len(rows) > 6 else ""
                w(f"- **Expected values ({int(rows['pass'].sum())}/{len(rows)} checks pass):** {vals}{more}")
            w("")
    w("## Pitfalls shown to be wrong (why the formulas look the way they do)")
    w("")
    w("| ID | Field | Wrong formulation | Evidence | Shown |")
    w("|---|---|---|---|---|")
    for _, r in res[res.kind == "pitfall shown wrong"].iterrows():
        w(f"| {r.id} | {r.calculated_field} | {r.context} | {r.note} | {'✅' if r['pass'] else '❌'} |")
    w("")
    w("## Drill-through and dashboard checks")
    w("")
    w("| ID | Field | Context | Tableau (emulated) | SQL expected | Pass |")
    w("|---|---|---|---|---|---|")
    num = lambda v: f"{v:,.2f}" if abs(v) >= 1000 else f"{v:,.6g}"
    for _, r in res[res.kind == "dashboard"].iterrows():
        w(f"| {r.id} | {r.calculated_field} | {r.context} | {num(r.tableau)} | {num(r.expected)} | "
          f"{'✅' if r['pass'] else '❌'} |")
    w("")
    return "\n".join(out) + "\n"


TAB.mkdir(exist_ok=True)
doc = build_doc()
if ARGS.write_docs:
    DOC_PATH.write_text(doc, encoding="utf-8")
in_sync = DOC_PATH.exists() and DOC_PATH.read_text(encoding="utf-8") == doc
RESULTS.append({"id": "DOC", "calculated_field": "documentation", "context":
                "tableau/calculated_fields.md matches the validated registry", "kind": "coverage / static",
                "tableau": None, "expected": None, "pass": in_sync,
                "note": "" if in_sync else "run with --write-docs to regenerate"})
res = pd.DataFrame(RESULTS)
res.to_csv(RESULTS_CSV, index=False)

# =============================================================================
# 8. REPORT
# =============================================================================
fmt = lambda v: "NULL" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:,.6f}"
print("=" * 118)
print("TABLEAU CALCULATED FIELDS — Tableau semantics emulated over the CSVs vs SQL-derived expected values")
print("=" * 118)
for kind in ["reference check", "fan-out guard", "dashboard", "pitfall shown wrong", "coverage / static"]:
    part = res[res.kind == kind]
    print(f"\n--- {kind.upper()} ({int(part['pass'].sum())}/{len(part)}) ---")
    for _, r in part.iterrows():
        flag = "PASS" if r["pass"] else "FAIL"
        if kind in ("pitfall shown wrong", "coverage / static"):
            print(f"  {flag}  {r.id:<4} {r.calculated_field:<34} {r.context}" + (f"\n               {r.note}" if r.note else ""))
        elif kind == "reference check" and r["pass"] and not r.note:
            continue                                          # keep the log short: failures and notes only
        else:
            print(f"  {flag}  {r.id:<4} {r.calculated_field:<34} {r.context:<58} tableau {fmt(r.tableau):>18}  "
                  f"expected {fmt(r.expected):>18}" + (f"\n               {r.note}" if r.note else ""))
mir = res[res.kind == "reference check"]
print(f"\n(reference checks passing without notes are not listed: {int((mir['pass'] & (mir.note == '')).sum())})")
print(f"measures: {len(calc_ids)}   helpers: {sum(c['id'][0] == 'H' for c in CALCS)}   parameters: {len(PARAMETERS)}")
print(f"checks: {len(res)}   PASS: {int(res['pass'].sum())}   FAIL: {int((~res['pass']).sum())}")
print("\nSCOPE: Tableau formula logic emulated in pandas, compared with SQL. NOT verified: Tableau syntax and runtime "
      "(pending a test in Tableau Desktop Public Edition).")
sys.exit(0 if res["pass"].all() else 1)
