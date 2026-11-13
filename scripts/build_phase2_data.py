"""
RetailPulse - Phase 2 data preparation.

Builds the three analysis-grain tables the spreadsheet workbook needs, and
computes the Python reference KPIs the spreadsheet will be checked against.

READ-ONLY with respect to dataset/raw/. Nothing is cleaned here - Phase 2 is
still exploration. The only transformations are joins and derived columns that
a spreadsheet cannot practically do across 100k+ rows.

Output: /private/tmp/.../phase2/  (orders.parquet-equivalent CSVs + kpis.json)

Usage:  ./venv/bin/python -I scripts/build_phase2_data.py <outdir>
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "dataset" / "raw"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "dataset" / "interim")
OUT.mkdir(parents=True, exist_ok=True)

ENC = {"product_category_name_translation.csv": "utf-8-sig"}
L = lambda n: pd.read_csv(RAW / n, dtype=str, encoding=ENC.get(n, "utf-8"))

print("Loading raw tables (all as text, nothing coerced)...")
orders   = L("olist_orders_dataset.csv")
items    = L("olist_order_items_dataset.csv")
customers= L("olist_customers_dataset.csv")
reviews  = L("olist_order_reviews_dataset.csv")
sellers  = L("olist_sellers_dataset.csv")
products = L("olist_products_dataset.csv")
trans    = L("product_category_name_translation.csv")

# ---------------------------------------------------------------- typing ----
for c in ["order_purchase_timestamp", "order_delivered_customer_date",
          "order_estimated_delivery_date"]:
    orders[c] = pd.to_datetime(orders[c])
items["price"] = items.price.astype(float)
items["freight_value"] = items.freight_value.astype(float)
reviews["review_score"] = reviews.review_score.astype(int)

# Revenue eligibility, per documentation/kpi_definitions.md:
# revenue excludes canceled and unavailable orders.
EXCLUDED_STATUSES = {"canceled", "unavailable"}
orders["revenue_eligible"] = (~orders.order_status.isin(EXCLUDED_STATUSES)).astype(int)

# ------------------------------------------------- English category names ----
# LEFT JOIN, never INNER: 13 products sit in 2 untranslated categories and an
# inner join would silently delete them (data quality issue Q03).
MANUAL = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
}
cat_map = dict(zip(trans.product_category_name, trans.product_category_name_english))
cat_map.update(MANUAL)
products["category_en"] = (products.product_category_name.map(cat_map)
                           .fillna(products.product_category_name)
                           .fillna("unknown"))

# ------------------------------------------------------- ITEM-GRAIN table ----
# One row per product line. This is where revenue and category live.
print("Building item-grain table...")
it = (items[["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"]]
      .merge(products[["product_id", "category_en"]], on="product_id", how="left")
      .merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
      .merge(orders[["order_id", "order_status", "order_purchase_timestamp",
                     "revenue_eligible"]], on="order_id", how="left"))
it["order_month"] = it.order_purchase_timestamp.dt.strftime("%Y-%m")
it["order_date"]  = it.order_purchase_timestamp.dt.date
items_out = it[["order_id", "order_date", "order_month", "order_status",
                "revenue_eligible", "category_en", "seller_id", "seller_state",
                "price", "freight_value"]].copy()
assert len(items_out) == 112650, len(items_out)

# ----------------------------------------------------- REVIEW-GRAIN table ----
# One row per review record. 99,224 rows; review_id is NOT unique (Q02).
print("Building review-grain table...")
reviews_out = reviews[["review_id", "order_id", "review_score"]].copy()
assert len(reviews_out) == 99224, len(reviews_out)

# ------------------------------------------------------ ORDER-GRAIN table ----
# One row per order. THE safe table to pivot: every other table fans out.
print("Building order-grain table...")
rev_by_order = (items.groupby("order_id", as_index=False)
                .agg(item_count=("order_item_id", "size"),
                     order_revenue=("price", "sum"),
                     order_freight=("freight_value", "sum")))

# Reviews aggregated to order level FIRST. 547 orders carry >1 review; joining
# raw reviews to orders would duplicate order rows and double-count revenue.
rev_by_order_review = (reviews.groupby("order_id", as_index=False)
                       .agg(review_score_avg=("review_score", "mean"),
                            review_count=("review_id", "size")))

o = (orders.merge(customers[["customer_id", "customer_unique_id", "customer_state",
                             "customer_city"]], on="customer_id", how="left")
     .merge(rev_by_order, on="order_id", how="left")
     .merge(rev_by_order_review, on="order_id", how="left"))

o["order_date"]  = o.order_purchase_timestamp.dt.date
o["order_month"] = o.order_purchase_timestamp.dt.strftime("%Y-%m")
o["order_year"]  = o.order_purchase_timestamp.dt.year
o["is_delivered"] = (o.order_status == "delivered").astype(int)
o["has_items"]    = o.item_count.notna().astype(int)
o["item_count"]   = o.item_count.fillna(0).astype(int)
o["order_revenue"] = o.order_revenue.fillna(0.0)
o["order_freight"] = o.order_freight.fillna(0.0)
o["review_count"]  = o.review_count.fillna(0).astype(int)

# Delivery metrics only where a real delivery date exists (Q01: 8 'delivered'
# orders have none, so the denominator is 96,476 and not 96,478).
has_dd = o.order_delivered_customer_date.notna()
o["delivery_days"] = pd.NA
o.loc[has_dd, "delivery_days"] = ((o.loc[has_dd, "order_delivered_customer_date"]
                                   - o.loc[has_dd, "order_purchase_timestamp"])
                                  .dt.total_seconds() / 86400).round(2)
# Compute lateness from the UNROUNDED difference, then round only for display.
# Rounding first would reclassify orders late by under ~7 minutes as on-time.
_delay_exact = ((o.loc[has_dd, "order_delivered_customer_date"]
                 - o.loc[has_dd, "order_estimated_delivery_date"])
                .dt.total_seconds() / 86400)
o["delay_days"] = pd.NA
o.loc[has_dd, "delay_days"] = _delay_exact.round(2)
o["is_late"] = pd.NA
o.loc[has_dd, "is_late"] = (_delay_exact > 0).astype(int)

orders_out = o[["order_id", "customer_unique_id", "customer_state", "customer_city",
                "order_status", "revenue_eligible", "order_date", "order_month",
                "order_year", "is_delivered", "has_items", "item_count",
                "order_revenue", "order_freight", "delivery_days", "delay_days",
                "is_late", "review_score_avg", "review_count"]].copy()
assert len(orders_out) == 99441, len(orders_out)

# ----------------------------------------------- PYTHON REFERENCE KPIs ------
print("Computing Python reference KPIs...")
elig = orders_out[orders_out.revenue_eligible == 1]
elig_items = items_out[items_out.revenue_eligible == 1]
with_items = orders_out[orders_out.has_items == 1]
elig_with_items = elig[elig.has_items == 1]

kpis = {
    "total_orders_all":          int(len(orders_out)),
    "total_orders_with_items":   int(len(with_items)),
    "total_orders_eligible":     int(len(elig)),
    "total_orders_elig_items":   int(len(elig_with_items)),
    "delivered_orders":          int(orders_out.is_delivered.sum()),
    "canceled_orders":           int((orders_out.order_status == "canceled").sum()),
    "total_customers_unique":    int(orders_out.customer_unique_id.nunique()),
    "gmv_all_statuses":          round(float(items_out.price.sum()), 2),
    "revenue_eligible":          round(float(elig_items.price.sum()), 2),
    "freight_all_statuses":      round(float(items_out.freight_value.sum()), 2),
    "aov_eligible":              round(float(elig_items.price.sum()) / len(elig_with_items), 2),
    "aov_all_with_items":        round(float(items_out.price.sum()) / len(with_items), 2),
    "median_order_value_elig":   round(float(elig_with_items.order_revenue.median()), 2),
    "avg_review_score_reviewlevel": round(float(reviews_out.review_score.mean()), 4),
    "avg_review_score_orderlevel":  round(float(orders_out.review_score_avg.mean()), 4),
    "orders_with_review":        int(orders_out.review_count.gt(0).sum()),
    "review_rows":               int(len(reviews_out)),
    "orders_with_delivery_date": int(orders_out.delivery_days.notna().sum()),
    "avg_delivery_days":         round(float(pd.to_numeric(orders_out.delivery_days).mean()), 2),
    "median_delivery_days":      round(float(pd.to_numeric(orders_out.delivery_days).median()), 2),
    "late_orders":               int(pd.to_numeric(orders_out.is_late).sum()),
    "on_time_rate_pct":          round(float(1 - pd.to_numeric(orders_out.is_late).mean()) * 100, 2),
    "cancellation_rate_pct":     round(float((orders_out.order_status == "canceled").mean()) * 100, 4),
    "item_rows":                 int(len(items_out)),
}

# The fan-out demonstration: what joining at the wrong grain costs you.
payments = L("olist_order_payments_dataset.csv")
payments["payment_value"] = payments.payment_value.astype(float)
# Demo A - items x payments. Orders paid in instalments repeat their payment
# rows, which duplicates every item line of that order. Pure inflation.
naive_pay = items[["order_id", "price"]].merge(
    payments[["order_id", "payment_value"]], on="order_id", how="inner")
kpis["fanout_correct_gmv"] = round(float(items.price.sum()), 2)
kpis["fanout_pay_rows"] = int(len(naive_pay))
kpis["fanout_pay_gmv"] = round(float(naive_pay.price.sum()), 2)
kpis["fanout_pay_inflation_pct"] = round(
    (float(naive_pay.price.sum()) / float(items.price.sum()) - 1) * 100, 2)

# Demo B - items x reviews. Subtler and more dangerous: an INNER join both
# duplicates (547 orders have 2-3 reviews) AND silently drops (768 orders have
# none), so the error can land either side of the truth.
naive_rev = items[["order_id", "price"]].merge(
    reviews[["order_id", "review_score"]], on="order_id", how="inner")
kpis["fanout_rev_rows"] = int(len(naive_rev))
kpis["fanout_rev_gmv"] = round(float(naive_rev.price.sum()), 2)
kpis["fanout_rev_error_pct"] = round(
    (float(naive_rev.price.sum()) / float(items.price.sum()) - 1) * 100, 2)
kpis["fanout_rows_correct"] = int(len(items))

# ------------------------------------------------------------------ write ----
orders_out.to_csv(OUT / "orders_grain.csv", index=False)
items_out.to_csv(OUT / "items_grain.csv", index=False)
reviews_out.to_csv(OUT / "reviews_grain.csv", index=False)
(OUT / "python_kpis.json").write_text(json.dumps(kpis, indent=2))

print(f"\nWrote 3 tables + python_kpis.json to {OUT}")
print(f"  orders_grain  {len(orders_out):>7,} rows x {orders_out.shape[1]} cols")
print(f"  items_grain   {len(items_out):>7,} rows x {items_out.shape[1]} cols")
print(f"  reviews_grain {len(reviews_out):>7,} rows x {reviews_out.shape[1]} cols")
print("\nPython reference KPIs:")
for k, v in kpis.items():
    print(f"  {k:<32} {v:>18,}" if isinstance(v, (int, float)) else f"  {k:<32} {v}")
