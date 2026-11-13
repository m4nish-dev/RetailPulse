"""
RetailPulse - independent re-verification of the data quality issue register.

Recomputes the affected-record count for all 17 logged issues directly from
dataset/raw/, so no number in documentation/data_quality_report.md rests on a
figure copied from an earlier run. Read-only.

Usage: ./venv/bin/python -I scripts/verify_issue_register.py
"""
from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "dataset" / "raw"
ENC = {"product_category_name_translation.csv": "utf-8-sig"}
L = lambda n: pd.read_csv(RAW / n, dtype=str, encoding=ENC.get(n, "utf-8"))

orders  = L("olist_orders_dataset.csv")
items   = L("olist_order_items_dataset.csv")
pays    = L("olist_order_payments_dataset.csv")
revs    = L("olist_order_reviews_dataset.csv")
prods   = L("olist_products_dataset.csv")
geo     = L("olist_geolocation_dataset.csv")
trans   = L("product_category_name_translation.csv")

od = orders.copy()
for c in ["order_purchase_timestamp", "order_approved_at",
          "order_delivered_carrier_date", "order_delivered_customer_date",
          "order_estimated_delivery_date"]:
    od[c] = pd.to_datetime(od[c])

checks = []
def chk(qid, claimed, actual, what):
    checks.append({"id": qid, "claimed": claimed, "actual": int(actual),
                   "match": int(actual) == claimed, "measures": what})

# Q01 delivered status but no delivery date
chk("Q01", 8, ((od.order_status == "delivered")
               & od.order_delivered_customer_date.isna()).sum(),
    "orders with status='delivered' and NULL order_delivered_customer_date")

# Q02 review_id reused
vc = revs.review_id.value_counts()
chk("Q02", 789, (vc > 1).sum(), "distinct review_id values appearing >1 time")

# Q03 untranslated categories (products affected)
missing_cats = set(prods.product_category_name.dropna()) - set(trans.product_category_name)
chk("Q03", 13, prods.product_category_name.isin(missing_cats).sum(),
    "products whose category has no English translation")

# Q04 null product category
chk("Q04", 610, prods.product_category_name.isna().sum(),
    "products with NULL product_category_name")

# Q05 orders with no line items
chk("Q05", 775, (~orders.order_id.isin(set(items.order_id))).sum(),
    "orders with zero rows in order_items")

# Q06 partial months (<200 orders)
m = od.order_purchase_timestamp.dt.to_period("M").value_counts()
chk("Q06", 4, (m < 200).sum(), "calendar months containing fewer than 200 orders")

# Q07 orders in 2016
chk("Q07", 329, (od.order_purchase_timestamp.dt.year == 2016).sum(),
    "orders placed in calendar year 2016")

# Q08 delivered to customer before carrier handoff
chk("Q08", 23, (od.order_delivered_customer_date
                < od.order_delivered_carrier_date).sum(),
    "orders delivered to customer BEFORE carrier handoff")

# Q09 payment_value = 0
chk("Q09", 9, (pays.payment_value.astype(float) == 0).sum(),
    "payment rows with payment_value = 0")

# Q10 payment_installments = 0
chk("Q10", 2, (pays.payment_installments.astype(int) == 0).sum(),
    "payment rows with payment_installments = 0")

# Q11 payment_type not_defined
chk("Q11", 3, (pays.payment_type == "not_defined").sum(),
    "payment rows with payment_type='not_defined'")

# Q12 geolocation exact duplicate rows
chk("Q12", 261831, geo.duplicated().sum(), "exact duplicate rows in geolocation")

# Q13 missing product weight
chk("Q13", 2, prods.product_weight_g.isna().sum(),
    "products with NULL product_weight_g")

# Q14 orders with no review
chk("Q14", 768, (~orders.order_id.isin(set(revs.order_id))).sum(),
    "orders with zero rows in order_reviews")

# Q15 missing order_approved_at
chk("Q15", 160, orders.order_approved_at.isna().sum(),
    "orders with NULL order_approved_at")

# Q16 misspelled source columns
mis = [c for c in prods.columns if "lenght" in c]
chk("Q16", 2, len(mis), f"misspelled source column names: {mis}")

# Q17 reviews containing embedded newlines
emb = (revs.review_comment_message.fillna("").str.contains("\n")
       | revs.review_comment_title.fillna("").str.contains("\n"))
chk("Q17", 3852, emb.sum(), "review records whose comment text contains a newline")

df = pd.DataFrame(checks)
print("=" * 104)
print("INDEPENDENT RE-VERIFICATION OF THE ISSUE REGISTER (recomputed from dataset/raw/)")
print("=" * 104)
print(f"{'ID':<5}{'documented':>12}{'recomputed':>12}{'':>4}  what was measured")
print("-" * 104)
for _, r in df.iterrows():
    flag = "OK " if r["match"] else "XX "
    print(f"{r['id']:<5}{r['claimed']:>12,}{r['actual']:>12,}  {flag} {r['measures']}")
print("-" * 104)
bad = df[~df.match]
print(f"Issues verified : {len(df)}")
print(f"Counts matching : {int(df.match.sum())}")
print(f"MISMATCHES      : {len(bad)}")
if len(bad):
    print("\n!! The following documented counts are WRONG and must be corrected:")
    print(bad[["id", "claimed", "actual", "measures"]].to_string(index=False))

sev = {"Q01":"High","Q02":"High","Q06":"High","Q07":"High",
       "Q03":"Medium","Q04":"Medium","Q05":"Medium",
       "Q08":"Low","Q09":"Low","Q10":"Low","Q11":"Low","Q12":"Low",
       "Q13":"Low","Q14":"Low","Q15":"Low","Q16":"Low","Q17":"Info"}
print("\nSeverity distribution (from the register):")
s = pd.Series(sev).value_counts().reindex(["High","Medium","Low","Info"])
for k, v in s.items():
    print(f"  {k:<8}{v}")
print(f"  {'TOTAL':<8}{s.sum()}")
