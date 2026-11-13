# Cleaned Datasets

**These files are not committed to Git.** They are a derived artifact — about
90 MB across 9 CSVs — and they regenerate exactly from the raw data in roughly
two minutes.

## Why they are not in version control

Committing them would add ~90 MB to the repository on every rebuild, for data
that is fully reproducible from inputs the repo already describes. The raw
Olist CSVs are themselves excluded (licensed, 120 MB), so the reproducible
chain is: **download raw → run one notebook → cleaned data appears here.**

This is standard practice: version the *code that produces* data, not the data.

## How to regenerate them

```bash
cd /path/to/RetailPulse
source venv/bin/activate

# 1. Raw data must be in dataset/raw/ first.
#    See documentation/dataset_setup.md if it is not.
ls dataset/raw/*.csv        # expect 9 files

# 2. Run the cleaning notebook end to end
jupyter nbconvert --to notebook --execute --inplace \
    notebooks/02_data_cleaning.ipynb

# 3. Confirm
ls -lh dataset/cleaned/
```

The notebook asserts its own results: if any row count, key, relationship or
revenue total fails to reconcile, it raises an error rather than writing a
quietly wrong file. A clean run means all 34 validation checks passed.

## What gets produced

| File | Rows | Grain |
|---|---|---|
| `orders_clean.csv` | 99,441 | one row per order (+23 derived columns) |
| `order_items_clean.csv` | 112,650 | one row per product line |
| `order_payments_clean.csv` | 103,886 | one row per payment |
| `order_reviews_clean.csv` | 99,224 | one row per review record |
| `customers_clean.csv` | 99,441 | one row per order-level customer id |
| `products_clean.csv` | 32,951 | one row per product |
| `sellers_clean.csv` | 3,095 | one row per seller |
| `category_translation_clean.csv` | 73 | lookup (71 source + 2 added by hand) |
| `geolocation_clean.csv` | 19,015 | one row per zip prefix (aggregated) |

**Mind the grain.** `orders_clean` is the only table safe to aggregate for
order-level measures. Joining the others without aggregating first duplicates
revenue — see `reports/excel_exploration_report.md` for the measured damage.

Full details: `reports/data_cleaning_report.md` and
`documentation/cleaning_decisions.md`.
