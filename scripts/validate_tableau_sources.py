"""
RetailPulse - independent validation of the Tableau analytical sources.

Three independent paths are compared for every source:

  1. EXPORT   tableau/data/analytical/<source>.csv (written by
              scripts/export_tableau_sources.py from sql/09_dashboard_sources.sql)
  2. SQL      the same query re-run live (CSV == SQL), plus reconciliation
              against the EXISTING validated views (vw_customer_summary,
              vw_category_performance, vw_seller_performance)
  3. PANDAS   every source rebuilt from scratch from dataset/cleaned/*.csv,
              never reading the exports or the SQL file

No expected value is typed in by hand. Every "expected" figure is computed
here from the cleaned data or read from an existing view.

Read-only: the MySQL session is set READ ONLY; nothing is written anywhere.
Exit code 1 if any check fails.

Usage:  ./venv/bin/python scripts/validate_tableau_sources.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from export_tableau_sources import load_sources, run          # noqa: E402

from rp_db import ConfigError, get_connection                   # noqa: E402

CLEAN = ROOT / "dataset" / "cleaned"
EXP = ROOT / "tableau" / "data" / "analytical"
RESULTS: list[dict] = []
# SQL rounds exported averages to 4 or 6 decimals (exact decimal, half-up).
# The pandas rebuild keeps the EXACT value, and a correctly rounded export can
# differ from it by at most half a unit in the last place - never more.
HALF4 = 0.5e-4 + 1e-9
HALF6 = 0.5e-6 + 1e-9


def check(source, name, ok, detail=""):
    RESULTS.append({"source": source, "check": name, "pass": bool(ok), "detail": detail})


def cents(s):
    """Money to integer cents, so sums compare exactly."""
    return np.round(pd.to_numeric(s).astype(float) * 100).astype("int64")


def close(a, b, tol):
    a = pd.to_numeric(a).astype(float).to_numpy()
    b = pd.to_numeric(b).astype(float).to_numpy()
    both_nan = np.isnan(a) & np.isnan(b)
    return bool(np.all(both_nan | (np.abs(a - b) <= tol)))


def frame_equal(left, right, key, money=(), ints=(), approx=None, text=()):
    """Compare two frames on key; returns (ok, message)."""
    approx = approx or {}
    m = left.merge(right, on=key, how="outer", suffixes=("_l", "_r"), indicator=True)
    if (m["_merge"] != "both").any():
        return False, f"{(m['_merge'] != 'both').sum()} keys on one side only"
    bad = []
    for c in money:
        if not (cents(m[c + "_l"].fillna(0)) == cents(m[c + "_r"].fillna(0))).all():
            bad.append(c)
    for c in ints:
        l, r = m[c + "_l"], m[c + "_r"]
        if not ((l.isna() & r.isna()) | (l.astype(float) == r.astype(float))).all():
            bad.append(c)
    for c, tol in approx.items():
        if not close(m[c + "_l"], m[c + "_r"], tol):
            bad.append(c)
    for c in text:
        l, r = m[c + "_l"].astype("string"), m[c + "_r"].astype("string")
        if not ((l.isna() & r.isna()) | (l == r)).fillna(False).all():
            bad.append(c)
    return (not bad), ("all columns match" if not bad else f"mismatch in {bad}")


# ---------------------------------------------------------------------------
# Load the independent inputs
# ---------------------------------------------------------------------------
TS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
      "order_delivered_customer_date"]
orders = pd.read_csv(CLEAN / "orders_clean.csv", parse_dates=TS + ["order_date"], low_memory=False)
items = pd.read_csv(CLEAN / "order_items_clean.csv", low_memory=False,
                    usecols=["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"])
reviews = pd.read_csv(CLEAN / "order_reviews_clean.csv", low_memory=False)
products = pd.read_csv(CLEAN / "products_clean.csv", low_memory=False)
sellers = pd.read_csv(CLEAN / "sellers_clean.csv", dtype={"seller_zip_code_prefix": str})

for c in ["revenue_eligible", "delivery_measurable", "stage_timing_valid", "in_stable_window"]:
    orders[c] = orders[c].astype(str).eq("True")
orders["is_late"] = orders.is_late.map({True: 1, False: 0, "True": 1, "False": 0})
reviews["rbd"] = reviews.review_before_delivery.map({True: 1, False: 0, "True": 1, "False": 0})

items = items.merge(products[["product_id", "product_category_name_english"]], on="product_id", how="left")
CAT = "product_category_name_english"
items["category"] = items[CAT]
items = items.merge(orders[["order_id", "revenue_eligible", "order_date"]], on="order_id", how="left")
assert len(items) == 112_650, "item join multiplied rows"
elig_items = items[items.revenue_eligible]
TOTAL_REVENUE_CENTS = int(cents(elig_items.price).sum())

try:
    conn = get_connection(read_only=True)                       # app account from .env
except ConfigError as e:
    sys.exit(f"CONFIG ERROR: {e}")
q = lambda sql: run(conn, sql)
SOURCES = load_sources()
exp = {n: pd.read_csv(EXP / f"{n}.csv", keep_default_na=True, low_memory=False) for n in SOURCES}


def generic(source, key, required):
    """Checks every source gets: CSV == live SQL, grain, nulls, duplicates."""
    df = exp[source]
    live = q(SOURCES[source])
    live_csv = pd.read_csv(pd.io.common.StringIO(live.to_csv(index=False)), low_memory=False)
    same = (list(df.columns) == list(live_csv.columns) and len(df) == len(live_csv)
            and df.reset_index(drop=True).equals(live_csv.reset_index(drop=True)))
    check(source, "exported CSV identical to live SQL result", same,
          f"{len(df):,} rows x {df.shape[1]} cols")
    check(source, f"grain unique on {key}", not df.duplicated(key).any(),
          f"{df.duplicated(key).sum()} duplicate keys")
    check(source, "no fully duplicated rows", not df.duplicated().any())
    nulls = {c: int(df[c].isna().sum()) for c in required if df[c].isna().any()}
    check(source, "no NULLs in required columns", not nulls, str(nulls) if nulls else "none")
    return df


# ===========================================================================
# A. RFM
# ===========================================================================
S = "rfm_customer_segments"
rfm = generic(S, ["customer_unique_id"],
              ["customer_unique_id", "customer_order_count", "first_purchase_date",
               "last_purchase_date", "frequency", "monetary_value", "rfm_segment", "rfm_scored"])

# pandas rebuild
o = orders
max_ts = o.order_purchase_timestamp.max()
allp = o.groupby("customer_unique_id").agg(
    customer_order_count=("order_id", "size"),
    first_purchase_date=("order_purchase_timestamp", "min"),
    last_purchase_date=("order_purchase_timestamp", "max")).reset_index()
order_rev = elig_items.groupby("order_id").price.apply(lambda s: int(cents(s).sum())).rename("rev_cents")
eo = o[o.revenue_eligible].merge(order_rev, left_on="order_id", right_index=True)   # eligible WITH items
el = eo.groupby("customer_unique_id").agg(
    last_ts=("order_purchase_timestamp", "max"), frequency=("order_id", "size"),
    rev_cents=("rev_cents", "sum")).reset_index()
el["recency_days"] = (max_ts.normalize() - el.last_ts.dt.normalize()).dt.days
n = len(el)
el["r_score"] = 1 + (5 * (el.recency_days.rank(method="min", ascending=False).astype(int) - 1)) // n
el["m_score"] = 1 + (5 * (el.rev_cents.rank(method="min", ascending=True).astype(int) - 1)) // n
el["f_score"] = np.select([el.frequency >= 3, el.frequency == 2], [5, 3], 1)


def seg(r, f, m):
    if r >= 4 and f >= 3 and m >= 4: return "Champions"
    if r >= 3 and f >= 3: return "Loyal Customers"
    if r >= 4 and f == 1 and m >= 3: return "Potential Loyalists"
    if r <= 2 and m >= 4: return "At Risk"
    if r <= 2: return "Lost"
    return "Needs Attention"


el["rfm_segment"] = [seg(*t) for t in zip(el.r_score, el.f_score, el.m_score)]
el["monetary_value"] = el.rev_cents / 100
pr = allp.merge(el, on="customer_unique_id", how="left")
pr["rfm_segment"] = pr.rfm_segment.fillna("Not scored")
pr["rfm_scored"] = pr.r_score.notna().astype(int)
pr["frequency"] = pr.frequency.fillna(0)
pr["monetary_value"] = pr.monetary_value.fillna(0)
for c in ["first_purchase_date", "last_purchase_date"]:
    pr[c] = pr[c].dt.strftime("%Y-%m-%d")
pr["last_eligible_purchase_date"] = pr.last_ts.dt.strftime("%Y-%m-%d")

check(S, "people = distinct customer_unique_id in orders (pandas)",
      len(rfm) == o.customer_unique_id.nunique(), f"{len(rfm):,} vs {o.customer_unique_id.nunique():,}")
check(S, "uses customer_unique_id, not customer_id",
      len(rfm) != o.customer_id.nunique() and set(rfm.customer_unique_id) == set(o.customer_unique_id),
      f"customer_id would give {o.customer_id.nunique():,}")
check(S, "scored people = people with eligible orders with items (pandas)",
      int(rfm.rfm_scored.sum()) == n, f"{int(rfm.rfm_scored.sum()):,} vs {n:,}")
check(S, "monetary total = eligible item revenue (pandas, to the cent)",
      int(cents(rfm.monetary_value).sum()) == TOTAL_REVENUE_CENTS,
      f"{cents(rfm.monetary_value).sum()/100:,.2f}")
ok, msg = frame_equal(rfm, pr, "customer_unique_id", money=["monetary_value"],
                      ints=["customer_order_count", "frequency", "recency_days", "r_score",
                            "f_score", "m_score", "rfm_scored"],
                      text=["first_purchase_date", "last_purchase_date",
                            "last_eligible_purchase_date", "rfm_segment"])
check(S, "every customer row identical to pandas rebuild (R/F/M, scores, segment, dates)", ok, msg)
check(S, "F score is ordinal {1,3,5} only (not quintiles)",
      set(rfm.f_score.dropna().astype(int)) <= {1, 3, 5},
      str(rfm.f_score.value_counts().sort_index().to_dict()))
check(S, "R and M scores in 1..5", rfm.r_score.dropna().between(1, 5).all()
      and rfm.m_score.dropna().between(1, 5).all())
tie_r = rfm.dropna(subset=["r_score"]).groupby("recency_days").r_score.nunique().max()
tie_m = rfm.dropna(subset=["m_score"]).groupby("monetary_value").m_score.nunique().max()
check(S, "tied customers always share a score", tie_r == 1 and tie_m == 1)
vcs = q("SELECT customer_unique_id, total_orders, historical_value, "
        "DATE_FORMAT(first_order_date,'%Y-%m-%d') f, DATE_FORMAT(last_order_date,'%Y-%m-%d') l "
        "FROM vw_customer_summary")
mm = rfm.merge(vcs, on="customer_unique_id", how="outer", indicator=True)
check(S, "reconciles with vw_customer_summary per person (orders, value, dates)",
      (mm._merge == "both").all()
      and (mm.customer_order_count == mm.total_orders.astype(int)).all()
      and (cents(mm.monetary_value) == cents(mm.historical_value)).all()
      and (mm.first_purchase_date == mm.f).all() and (mm.last_purchase_date == mm.l).all(),
      f"{len(vcs):,} people in view")

# ===========================================================================
# B. Cohort retention
# ===========================================================================
S = "cohort_retention"
coh = generic(S, ["cohort_month", "months_since_acquisition"],
              ["cohort_month", "months_since_acquisition", "activity_month",
               "cohort_customers", "is_observed", "max_observed_offset"])
first = o.groupby("customer_unique_id").order_purchase_timestamp.min().rename("first_ts")
mem = first[(first >= "2017-01-01") & (first < "2018-09-01")].reset_index()
mem["cohort"] = mem.first_ts.dt.to_period("M")
act = o[["customer_unique_id", "order_purchase_timestamp"]].merge(mem, on="customer_unique_id")
act["k"] = (act.order_purchase_timestamp.dt.to_period("M") - act.cohort).apply(lambda x: x.n)
cnt = act.groupby(["cohort", "k"]).customer_unique_id.nunique()
sizes = mem.groupby("cohort").size()
rows = []
for c, size in sizes.items():
    for k in range(20):
        a_month = c + k
        observed = a_month <= pd.Period("2018-08", "M")
        active = int(cnt.get((c, k), 0)) if observed else np.nan
        rows.append({"cohort_month": str(c), "months_since_acquisition": k,
                     "activity_month": str(a_month), "cohort_customers": int(size),
                     "is_observed": int(observed),
                     "max_observed_offset": (pd.Period("2018-08", "M") - c).n,
                     "active_customers": active,
                     "returning_customers": active if k > 0 else np.nan,
                     "retention_pct": active / size * 100 if observed else np.nan})
pc = pd.DataFrame(rows)
check(S, "20 cohorts x 20 offsets = 400 rows", len(coh) == 400 and coh.cohort_month.nunique() == 20)
ok, msg = frame_equal(coh, pc, ["cohort_month", "months_since_acquisition"],
                      ints=["cohort_customers", "is_observed", "max_observed_offset",
                            "active_customers", "returning_customers"],
                      approx={"retention_pct": HALF4}, text=["activity_month"])
check(S, "every cell identical to pandas rebuild (calendar-month offsets)", ok, msg)
check(S, "cohort members = people first buying 2017-01..2018-08 (pandas)",
      int(coh[coh.months_since_acquisition == 0].cohort_customers.sum()) == len(mem), f"{len(mem):,}")
vc = q("SELECT cohort_month, COUNT(*) n FROM vw_customer_summary "
       "WHERE cohort_month BETWEEN '2017-01' AND '2018-08' GROUP BY cohort_month")
cz = coh[coh.months_since_acquisition == 0].merge(vc, on="cohort_month")
check(S, "cohort sizes = vw_customer_summary.cohort_month counts",
      len(cz) == 20 and (cz.cohort_customers == cz.n.astype(int)).all())
unobs = coh[coh.is_observed == 0]
check(S, "unobserved cells are NULL, never 0 (right-censoring)",
      unobs[["active_customers", "returning_customers", "retention_pct"]].isna().all().all()
      and (pd.PeriodIndex(unobs.activity_month, freq="M") > pd.Period("2018-08", "M")).all(),
      f"{len(unobs)} unobserved cells")
obs = coh[coh.is_observed == 1]
check(S, "observed cells have no NULL retention; offset 0 = 100%",
      obs.retention_pct.notna().all()
      and (coh[coh.months_since_acquisition == 0].retention_pct == 100).all(),
      f"{len(obs)} observed cells")
check(S, "returning <= cohort size everywhere",
      (obs.active_customers <= obs.cohort_customers).all())
check(S, "retention_pct = active / cohort x 100",
      close(obs.retention_pct, obs.active_customers / obs.cohort_customers * 100, HALF4))

# ===========================================================================
# C. Product performance
# ===========================================================================
S = "product_performance"
prod = generic(S, ["product_id"], ["product_id", "category", "order_count", "units_sold",
                                   "product_revenue", "freight_value", "units_all_statuses"])
g = items.groupby("product_id")
pp = pd.DataFrame({
    "category": g.category.first(),
    "order_count": elig_items.groupby("product_id").order_id.nunique(),
    "units_sold": elig_items.groupby("product_id").size(),
    "product_revenue": elig_items.groupby("product_id").price.apply(lambda s: cents(s).sum() / 100),
    "avg_item_price": elig_items.groupby("product_id").price.mean(),
    "freight_value": elig_items.groupby("product_id").freight_value.apply(lambda s: cents(s).sum() / 100),
    "avg_freight_value": elig_items.groupby("product_id").freight_value.mean(),
    "seller_count": elig_items.groupby("product_id").seller_id.nunique(),
    "units_all_statuses": g.size()}).reset_index()
for c in ["order_count", "units_sold", "product_revenue", "freight_value", "seller_count"]:
    pp[c] = pp[c].fillna(0)
check(S, "one row per product in the catalogue (pandas)",
      len(prod) == products.product_id.nunique(), f"{len(prod):,}")
ok, msg = frame_equal(prod, pp, "product_id", money=["product_revenue", "freight_value"],
                      ints=["order_count", "units_sold", "seller_count", "units_all_statuses"],
                      approx={"avg_item_price": HALF4, "avg_freight_value": HALF4}, text=["category"])
check(S, "every product row identical to pandas rebuild", ok, msg)
check(S, "revenue total = eligible item revenue (pandas, to the cent)",
      int(cents(prod.product_revenue).sum()) == TOTAL_REVENUE_CENTS)
check(S, "units total = eligible item rows (no join multiplication)",
      int(prod.units_sold.sum()) == len(elig_items), f"{len(elig_items):,}")
check(S, "all-status units = all 112,650 item rows",
      int(prod.units_all_statuses.sum()) == len(items))
vcp = q("SELECT category, SUM(revenue) revenue, SUM(items_sold) items FROM vw_category_performance GROUP BY category")
roll = prod.groupby("category").agg(rev=("product_revenue", "sum"), units=("units_sold", "sum")).reset_index()
roll = roll[roll.units > 0].merge(vcp, on="category", how="outer")
check(S, "category roll-up = vw_category_performance (revenue and items)",
      roll.notna().all().all() and (cents(roll.rev) == cents(roll.revenue)).all()
      and (roll.units == roll["items"].astype(int)).all())

# ===========================================================================
# D. Seller x category
# ===========================================================================
S = "seller_category_performance"
sc = generic(S, ["seller_id", "category"],
             ["seller_id", "seller_state", "category", "order_count", "item_count",
              "product_revenue", "freight_value", "delivery_measurable_orders",
              "late_orders", "dispatch_measurable_orders"])
nsel = items.groupby("order_id").seller_id.nunique().rename("n_sellers")
po = elig_items[["seller_id", "category", "order_id"]].drop_duplicates()
po = po.merge(orders[["order_id", "delivery_measurable", "delivery_days", "is_late",
                      "stage_timing_valid", "order_approved_at", "order_delivered_carrier_date"]],
              on="order_id").merge(nsel, left_on="order_id", right_index=True)
po["dispatch_ok"] = po.stage_timing_valid & (po.n_sellers == 1)
po["dispatch_days"] = np.where(po.dispatch_ok, (po.order_delivered_carrier_date - po.order_approved_at)
                               .dt.total_seconds() / 86400, np.nan)
gk = ["seller_id", "category"]
sales = elig_items.groupby(gk).agg(order_count=("order_id", "nunique"), item_count=("price", "size"),
                                   product_revenue=("price", lambda s: cents(s).sum() / 100),
                                   freight_value=("freight_value", lambda s: cents(s).sum() / 100))
dl = po.groupby(gk).agg(orders_shared_with_other_sellers=("n_sellers", lambda s: int((s > 1).sum())),
                        delivery_measurable_orders=("delivery_measurable", "sum"),
                        late_orders=("is_late", lambda s: int(s[po.loc[s.index, "delivery_measurable"]].sum())),
                        dispatch_measurable_orders=("dispatch_ok", "sum"),
                        avg_dispatch_days=("dispatch_days", "mean"))
dl["avg_delivery_days"] = po[po.delivery_measurable].groupby(gk).delivery_days.mean()
ps = sales.join(dl).reset_index()
ps["late_pct"] = ps.late_orders / ps.delivery_measurable_orders.replace(0, np.nan) * 100
ok, msg = frame_equal(sc, ps, gk, money=["product_revenue", "freight_value"],
                      ints=["order_count", "item_count", "orders_shared_with_other_sellers",
                            "delivery_measurable_orders", "late_orders", "dispatch_measurable_orders"],
                      approx={"avg_delivery_days": HALF4, "late_pct": HALF4, "avg_dispatch_days": HALF6})
check(S, "every (seller, category) row identical to pandas rebuild", ok, msg)
check(S, "revenue total = eligible item revenue (pandas, to the cent)",
      int(cents(sc.product_revenue).sum()) == TOTAL_REVENUE_CENTS)
check(S, "item total = eligible item rows (additive, no multiplication)",
      int(sc.item_count.sum()) == len(elig_items))
vsp = q("SELECT seller_id, revenue, items_sold FROM vw_seller_performance")
sr = sc.groupby("seller_id").agg(rev=("product_revenue", "sum"), it=("item_count", "sum")).reset_index() \
       .merge(vsp, on="seller_id", how="outer")
check(S, "seller roll-up = vw_seller_performance (revenue, items) for every seller",
      sr.notna().all().all() and (cents(sr.rev) == cents(sr.revenue)).all()
      and (sr.it == sr.items_sold.astype(int)).all(), f"{len(vsp):,} sellers")
cr = sc.groupby("category").product_revenue.sum().reset_index().merge(vcp, on="category")
check(S, "category roll-up = vw_category_performance revenue",
      len(cr) == vcp.shape[0] and (cents(cr.product_revenue) == cents(cr.revenue)).all())
check(S, "order_count is non-additive as documented (sum >= distinct eligible orders)",
      int(sc.order_count.sum()) >= elig_items.order_id.nunique(),
      f"sum {int(sc.order_count.sum()):,} vs distinct {elig_items.order_id.nunique():,}")
check(S, "late_pct only where a delivery population exists",
      sc.loc[sc.delivery_measurable_orders == 0, "late_pct"].isna().all()
      and sc.loc[sc.delivery_measurable_orders > 0, "late_pct"].notna().all())

# ===========================================================================
# E. Delivery stages
# ===========================================================================
S = "delivery_stage_orders"
ds = generic(S, ["order_id"], list(exp[S].columns))
t = orders
valid = (t[TS].notna().all(axis=1)
         & (t.order_purchase_timestamp <= t.order_approved_at)
         & (t.order_approved_at <= t.order_delivered_carrier_date)
         & (t.order_delivered_carrier_date <= t.order_delivered_customer_date))   # from timestamps, not the flag
v = t[valid]
sec = lambda a, b: (v[b] - v[a]).dt.total_seconds().astype("int64")
pdv = pd.DataFrame({"order_id": v.order_id,
                    "purchase_to_approval_seconds": sec(TS[0], TS[1]),
                    "approval_to_carrier_seconds": sec(TS[1], TS[2]),
                    "carrier_to_customer_seconds": sec(TS[2], TS[3]),
                    "total_seconds": sec(TS[0], TS[3])})
check(S, "population = orders whose timestamps are present and ordered (pandas, from timestamps)",
      len(ds) == len(pdv), f"{len(ds):,} vs {len(pdv):,}")
check(S, "population = stage_timing_valid flag",
      set(ds.order_id) == set(t[t.stage_timing_valid].order_id))
ok, msg = frame_equal(ds, pdv, "order_id", ints=["purchase_to_approval_seconds",
                      "approval_to_carrier_seconds", "carrier_to_customer_seconds", "total_seconds"])
check(S, "every order's stage seconds identical to pandas rebuild", ok, msg)
secs = ["purchase_to_approval_seconds", "approval_to_carrier_seconds", "carrier_to_customer_seconds"]
check(S, "no negative stage duration", (ds[secs + ["total_seconds"]] >= 0).all().all())
check(S, "stages sum exactly to total for every order", (ds[secs].sum(axis=1) == ds.total_seconds).all())
check(S, "days columns = seconds / 86400",
      all(close(ds[c.replace("seconds", "days")], ds[c] / 86400, HALF6) for c in secs + ["total_seconds"]))
check(S, "excluded = Q18 + Q08 + missing timestamps (accounted for)",
      len(ds) + int((~valid & t.delivery_measurable).sum()) == int(t.delivery_measurable.sum()),
      f"{int(t.delivery_measurable.sum()):,} measurable - {int((~valid & t.delivery_measurable).sum()):,} excluded")

S = "delivery_stage_summary"
ss = generic(S, ["stage_order"], list(exp[S].columns))
tot = pdv.total_seconds.sum()
exp_share = [pdv[c].sum() / tot * 100 for c in secs]
exp_days = [pdv[c].mean() / 86400 for c in secs] + [pdv.total_seconds.mean() / 86400]
check(S, "stage shares = ratio of summed seconds (pandas)",
      close(ss.share_pct.iloc[:3], pd.Series(exp_share), HALF4),
      " / ".join(f"{x:.2f}%" for x in exp_share))
check(S, "average days per stage = pandas", close(ss.avg_days, pd.Series(exp_days), HALF6),
      " / ".join(f"{x:.2f}" for x in exp_days))
check(S, "three shares add to 100", abs(ss.share_pct.iloc[:3].sum() - 100) < 1e-3)
check(S, "summary population = order-level rows", (ss.orders == len(ds)).all())
check(S, "summary consistent with order-level file",
      close(ss.avg_days.iloc[:3], pd.Series([ds[c.replace('seconds', 'days')].mean() for c in secs]), HALF6))

# ===========================================================================
# F. Category satisfaction
# ===========================================================================
S = "category_satisfaction"
cs = generic(S, ["category"], ["category", "order_count", "item_count"])
oc = items[["order_id", "category"]].drop_duplicates()
ncat = oc.groupby("order_id").size().rename("n_cat")
rv = oc.merge(reviews[["review_id", "order_id", "review_score", "rbd"]], on="order_id") \
       .merge(ncat, left_on="order_id", right_index=True)
check(S, "(review_id, order_id, category) unique: no review counted twice in a category",
      not rv.duplicated(["review_id", "order_id", "category"]).any())
gr = rv.groupby("category")
pcs = pd.DataFrame({
    "order_count": items.groupby("category").order_id.nunique(),
    "item_count": items.groupby("category").size(),
    "reviewed_orders": gr.order_id.nunique(),
    "review_count": gr.size(),
    "avg_review_score": gr.review_score.mean(),
    "one_star_pct": gr.review_score.apply(lambda s: (s == 1).mean() * 100),
    "five_star_pct": gr.review_score.apply(lambda s: (s == 5).mean() * 100),
    "reviews_before_delivery": gr.rbd.apply(lambda s: int((s == 1).sum())),
    "reviews_order_not_delivered": gr.rbd.apply(lambda s: int(s.isna().sum())),
    "reviews_after_arrival": gr.rbd.apply(lambda s: int((s == 0).sum())),
    "reviews_from_multi_category_orders": gr.n_cat.apply(lambda s: int((s > 1).sum()))})
after = rv[rv.rbd == 0].groupby("category")
pcs["avg_review_score_after_arrival"] = after.review_score.mean()
pcs["one_star_pct_after_arrival"] = after.review_score.apply(lambda s: (s == 1).mean() * 100)
pcs["pct_reviews_before_delivery"] = (pcs.reviews_before_delivery / pcs.review_count * 100)
od = oc.merge(orders[["order_id", "delivery_measurable", "is_late"]], on="order_id")
od = od[od.delivery_measurable]
pcs["delivery_measurable_orders"] = od.groupby("category").size()
pcs["late_orders"] = od.groupby("category").is_late.sum()
pcs["late_pct"] = (pcs.late_orders / pcs.delivery_measurable_orders * 100)
pcs = pcs.reset_index().rename(columns={"index": "category"})
ok, msg = frame_equal(cs, pcs, "category",
                      ints=["order_count", "item_count", "reviewed_orders", "review_count",
                            "reviews_before_delivery", "reviews_order_not_delivered",
                            "reviews_after_arrival", "reviews_from_multi_category_orders",
                            "delivery_measurable_orders", "late_orders"],
                      approx={c: HALF4 for c in ["avg_review_score", "one_star_pct", "five_star_pct",
                                                "pct_reviews_before_delivery",
                                                "avg_review_score_after_arrival",
                                                "one_star_pct_after_arrival", "late_pct"]})
check(S, "every category row identical to pandas rebuild", ok, msg)
reviews_with_cat = reviews[reviews.order_id.isin(items.order_id)]
dup = int((rv.groupby(["review_id", "order_id"]).size() - 1).sum())
check(S, "review_count total - multi-category duplicates = distinct reviews with a category",
      int(cs.review_count.sum()) - dup == len(reviews_with_cat),
      f"{int(cs.review_count.sum()):,} - {dup:,} = {len(reviews_with_cat):,} "
      f"(of {len(reviews):,}; {len(reviews) - len(reviews_with_cat):,} on item-less orders)")
rb_total = int(reviews_with_cat.rbd.eq(1).sum())
rb_dup = int(rv[rv.rbd == 1].groupby(["review_id", "order_id"]).size().sub(1).sum())
check(S, "pre-delivery reviews reconcile to the Q19 flag (after removing duplicates)",
      int(cs.reviews_before_delivery.sum()) - rb_dup == rb_total,
      f"{rb_total:,} of the {int(reviews.rbd.eq(1).sum()):,} Q19 reviews have a category")
check(S, "timing split complete: before + after + undelivered = review_count",
      (cs.reviews_before_delivery + cs.reviews_after_arrival + cs.reviews_order_not_delivered
       == cs.review_count).all())
check(S, "multi-category duplicates equal multi-category reviews minus their distinct count",
      int(cs.reviews_from_multi_category_orders.sum()) - dup
      == rv[rv.n_cat > 1][["review_id", "order_id"]].drop_duplicates().shape[0])

# ===========================================================================
# seller_scorecard (added in the measure audit, fix-Phase 4)
# ===========================================================================
S = "seller_scorecard"
sk = generic(S, ["seller_id"], ["seller_id", "orders_served", "delivery_measurable_orders",
                                "late_orders", "delivery_days_sum", "reviewed_orders", "poor_rated_orders"])
pairs = elig_items[["seller_id", "order_id"]].drop_duplicates().merge(
    orders[["order_id", "delivery_measurable", "is_late", "delivery_days"]], on="order_id")
oscore = reviews.groupby("order_id").review_score.mean().rename("score")
pairs = pairs.merge(oscore, left_on="order_id", right_index=True, how="left")
pairs["m"] = pairs.delivery_measurable
psk = pairs.groupby("seller_id").agg(
    orders_served=("order_id", "size"),
    delivery_measurable_orders=("m", "sum"),
    late_orders=("is_late", lambda x: int(x[pairs.loc[x.index, "m"]].sum())),
    delivery_days_sum=("delivery_days", lambda x: x[pairs.loc[x.index, "m"]].sum()),
    reviewed_orders=("score", "count"),
    review_score_sum=("score", "sum"),
    poor_rated_orders=("score", lambda x: int((x <= 2).sum()))).reset_index()
ok, msg = frame_equal(sk, psk, "seller_id",
                      ints=["orders_served", "delivery_measurable_orders", "late_orders",
                            "reviewed_orders", "poor_rated_orders"],
                      approx={"delivery_days_sum": 1e-6, "review_score_sum": HALF6})
check(S, "every seller row identical to pandas rebuild", ok, msg)
vsf = q("SELECT seller_id, orders_served, avg_delivery_days, late_pct, avg_review_score, "
        "poor_rated_orders FROM vw_seller_performance")
j = sk.merge(vsf, on="seller_id", how="outer", suffixes=("", "_v"), indicator=True)
dm = j.delivery_measurable_orders.replace(0, np.nan)
check(S, "same 3,053 sellers as vw_seller_performance, same orders_served",
      (j._merge == "both").all() and (j.orders_served == j.orders_served_v.astype(int)).all(),
      f"{len(vsf):,} sellers")
check(S, "reproduces every seller's published rates (late %, delivery days, rating, poor-rated)",
      close(j.late_orders / dm * 100, j.late_pct, 0.005 + 1e-9)
      and close(j.delivery_days_sum / dm, j.avg_delivery_days, 0.005 + 1e-9)
      and close(j.review_score_sum / j.reviewed_orders.replace(0, np.nan), j.avg_review_score, 0.0005 + 1e-9)
      and (j.poor_rated_orders == j.poor_rated_orders_v.astype(int)).all(),
      "view rates are rounded to 2-3 dp; tolerance = half a unit")
check(S, "pair grain: orders_served sums to distinct seller-order pairs, above distinct orders",
      int(sk.orders_served.sum()) == len(pairs) > elig_items.order_id.nunique(),
      f"{len(pairs):,} pairs vs {elig_items.order_id.nunique():,} orders")

# ===========================================================================
# dim_category
# ===========================================================================
S = "dim_category"
dc = generic(S, ["category"], ["category", "category_portuguese", "product_count"])
cats = set(dc.category)
check(S, "covers every category used by the other sources",
      set(prod.category) <= cats and set(sc.category) <= cats and set(cs.category) <= cats
      and set(vcp.category) <= cats, f"{len(cats)} categories")
check(S, "product counts sum to the catalogue", int(dc.product_count.sum()) == len(products))

conn.close()

# ---------------------------------------------------------------------------
res = pd.DataFrame(RESULTS)
print("=" * 112)
print("TABLEAU ANALYTICAL SOURCES — INDEPENDENT VALIDATION (export vs live SQL vs pandas vs existing views)")
print("=" * 112)
for src, grp in res.groupby("source", sort=False):
    print(f"\n{src}  ({int(grp['pass'].sum())}/{len(grp)})")
    for _, r in grp.iterrows():
        print(f"  {'PASS' if r['pass'] else 'FAIL'}  {r['check']}" + (f"  [{r.detail}]" if r.detail else ""))
print("\n" + "-" * 112)
print(f"checks: {len(res)}   PASS: {int(res['pass'].sum())}   FAIL: {int((~res['pass']).sum())}")
sys.exit(0 if res["pass"].all() else 1)
