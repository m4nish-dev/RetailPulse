"""
RetailPulse - Tableau data-readiness check (read-only).

Confirms the CSV files the Tableau dashboard connects to are complete and
consistent before (and after) they are opened in Tableau Desktop Public Edition:

  * the 14 tables in tableau/data/ and tableau/data/analytical/ are readable;
    row/column counts and MD5 hashes match both manifests; no other files
  * extracts have the same row counts as live MySQL (skipped with --offline)
  * primary keys unique and non-null (the grain of every table)
  * the 8 Tableau relationships (tableau/data_model.md §3): unique key on the
    root side, no orphans, no blank keys
  * dates valid; blanks exactly where designed (cohort, review timing, RFM)
  * eligible revenue identical across 7 sources (no join multiplication)
  * identifiers kept as 32-character hex text

Usage:  ./venv/bin/python scripts/check_tableau_data.py [--offline]
Exit code 1 on any failure.
"""
import argparse
import hashlib
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "tableau" / "data"
A = D / "analytical"
R = []


def ck(area, name, ok, detail=""):
    R.append((area, name, bool(ok), detail))


# grain of every table Tableau reads
PK = {"vw_order_summary": ["order_id"], "vw_customer_summary": ["customer_unique_id"],
      "vw_seller_performance": ["seller_id"], "vw_review_summary": ["review_id", "order_id"],
      "vw_category_performance": ["category", "order_month"],
      "rfm_customer_segments": ["customer_unique_id"], "cohort_retention": ["cohort_month", "months_since_acquisition"],
      "product_performance": ["product_id"], "seller_category_performance": ["seller_id", "category"],
      "delivery_stage_orders": ["order_id"], "delivery_stage_summary": ["stage_order"],
      "category_satisfaction": ["category"], "seller_scorecard": ["seller_id"], "dim_category": ["category"]}

# (data source, root table, key, related table, key) - must match tableau/data_model.md §3
RELATIONSHIPS = [
    ("RP Orders", "vw_order_summary", "order_id", "vw_review_summary", "order_id"),
    ("RP Orders", "vw_order_summary", "order_id", "delivery_stage_orders", "order_id"),
    ("RP Customers", "vw_customer_summary", "customer_unique_id", "rfm_customer_segments", "customer_unique_id"),
    ("RP Categories", "dim_category", "category", "vw_category_performance", "category"),
    ("RP Categories", "dim_category", "category", "product_performance", "category"),
    ("RP Categories", "dim_category", "category", "category_satisfaction", "category"),
    ("RP Sellers", "vw_seller_performance", "seller_id", "seller_scorecard", "seller_id"),
    ("RP Sellers", "vw_seller_performance", "seller_id", "seller_category_performance", "seller_id"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip the live MySQL comparison")
    args = ap.parse_args()

    files = sorted(D.glob("*.csv")) + sorted(A.glob("*.csv"))
    T = {p.stem: pd.read_csv(p, low_memory=False) for p in files if not p.name.startswith("_")}
    ck("files", "14 tables readable, no unexpected files", set(T) == set(PK), f"{len(T)} read")
    other = [p.name for p in list(D.iterdir()) + list(A.iterdir())
             if p.is_file() and p.suffix != ".csv" and p.name not in (".gitkeep", ".DS_Store")]
    ck("files", "data folders hold only CSV files (no credentials, no workbooks)", not other, f"other: {other or 'none'}")
    mf = pd.read_csv(D / "_manifest.csv").set_index("object")
    ma = pd.read_csv(A / "_manifest.csv").set_index("source")
    ck("files", "both manifests list exactly the tables present", set(mf.index) | set(ma.index) == set(PK))
    ck("files", "row/column counts match both manifests",
       all(T[o].shape == (r.rows, r.columns) for o, r in mf.iterrows())
       and all(T[o].shape == (r.rows, r.columns) for o, r in ma.iterrows()))
    ck("files", "every file byte-identical to its manifest MD5",
       all(hashlib.md5((D / f"{s}.csv").read_bytes()).hexdigest() == r.md5 for s, r in mf.iterrows())
       and all(hashlib.md5((A / f"{s}.csv").read_bytes()).hexdigest() == r.md5 for s, r in ma.iterrows()))

    live_rev = None
    if args.offline:
        ck("files", "live MySQL comparison", True, "skipped (--offline)")
    else:
        sys.path.insert(0, str(ROOT / "scripts"))
        from rp_db import get_connection
        c = get_connection(); cur = c.cursor()
        same = []
        for v in mf.index:
            cur.execute(f"SELECT COUNT(*) FROM `{v}`"); same.append(cur.fetchone()[0] == len(T[v]))
        cur.execute("SELECT SUM(order_revenue) FROM vw_order_summary WHERE revenue_eligible = 1")
        live_rev = float(cur.fetchone()[0]); c.close()
        ck("files", "view extracts have the same row counts as live MySQL", all(same))

    bad = [t for t, k in PK.items() if T[t].duplicated(k).any() or T[t][k].isna().any().any()]
    ck("keys", "grain/primary key unique and non-null in all 14 tables", not bad, f"failures: {bad or 'none'}")
    for ds, one, k1, many, k2 in RELATIONSHIPS:
        a = T[one][k1].astype(str); b = T[many][k2].dropna().astype(str)
        orphans = int((~b.isin(set(a))).sum()); nulls = int(T[many][k2].isna().sum())
        ck("relationships", f"{ds}: {one}.{k1} -> {many}.{k2}", a.is_unique and orphans == 0 and nulls == 0,
           f"root unique={a.is_unique}, orphans={orphans}, blank keys={nulls}")

    od = pd.to_datetime(T["vw_order_summary"].order_date, errors="coerce")
    ck("dates", "order_date parses (2016-09-04 .. 2018-10-17); November 2016 has no orders",
       od.notna().all() and str(od.min().date()) == "2016-09-04" and str(od.max().date()) == "2018-10-17"
       and not (od.dt.strftime("%Y-%m") == "2016-11").any())
    so = T["vw_order_summary"]
    ck("dates", "in_stable_window = 1 exactly for 2017-01 .. 2018-08",
       ((so.order_month.between("2017-01", "2018-08")).astype(int) == so.in_stable_window).all())
    rs = T["vw_review_summary"].review_creation_date.astype(str)
    ck("dates", "review_creation_date: one text format, all parse",
       pd.to_datetime(rs, errors="coerce").notna().all() and rs.str.len().nunique() == 1)

    coh = T["cohort_retention"]
    ck("blanks", "cohort: 190 unobserved cells blank, 210 observed non-blank",
       coh[coh.is_observed == 0].retention_pct.isna().all() and coh[coh.is_observed == 0].active_customers.isna().all()
       and coh[coh.is_observed == 1].retention_pct.notna().all() and int((coh.is_observed == 0).sum()) == 190)
    rv = T["vw_review_summary"].review_before_delivery
    ck("blanks", "review_before_delivery: 4,795 = 1; blank only for undelivered orders",
       int((rv == 1).sum()) == 4795 and set(rv.dropna().unique()) <= {0, 1})
    rfm = T["rfm_customer_segments"]
    ck("blanks", "RFM scores blank exactly for the 1,113 unscored people; 94,983 scored",
       int(rfm.r_score.isna().sum()) == int((rfm.rfm_scored == 0).sum()) == 1113 and int(rfm.rfm_scored.sum()) == 94983)

    money = {"vw_order_summary": so.query("revenue_eligible == 1").order_revenue.sum(),
             "vw_category_performance": T["vw_category_performance"].revenue.sum(),
             "vw_seller_performance": T["vw_seller_performance"].revenue.sum(),
             "vw_customer_summary": T["vw_customer_summary"].historical_value.sum(),
             "product_performance": T["product_performance"].product_revenue.sum(),
             "seller_category_performance": T["seller_category_performance"].product_revenue.sum(),
             "rfm_customer_segments": T["rfm_customer_segments"].monetary_value.sum()}
    ref = live_rev if live_rev is not None else money["vw_order_summary"]
    ck("revenue", "eligible revenue identical in 7 sources" + ("" if args.offline else " and live MySQL"),
       all(round(v * 100) == round(ref * 100) for v in money.values()), f"BRL {ref:,.2f}")

    ck("types", "32-character hex IDs intact (order, person, seller, product)",
       all(T[t][c].astype(str).str.fullmatch(r"[0-9a-f]{32}").all()
           for t, c in [("vw_order_summary", "order_id"), ("vw_order_summary", "customer_unique_id"),
                        ("vw_seller_performance", "seller_id"), ("product_performance", "product_id")]))
    ck("types", "month keys are 'YYYY-MM' text (import as String in Tableau)",
       all(T[t][c].astype(str).str.fullmatch(r"\d{4}-\d{2}").all()
           for t, c in [("vw_category_performance", "order_month"), ("cohort_retention", "cohort_month")]))

    for area, name, ok, detail in R:
        print(f"  {'PASS' if ok else 'FAIL'}  [{area}] {name}" + (f"  — {detail}" if detail else ""))
    n = sum(r[2] for r in R)
    print(f"checks: {len(R)}   PASS: {n}   FAIL: {len(R) - n}")
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
