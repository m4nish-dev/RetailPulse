# Dataset Setup Guide

How to obtain the Olist dataset and place it correctly for this project.

---

## 1. What you are downloading

**Brazilian E-Commerce Public Dataset by Olist**
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Olist is a Brazilian e-commerce marketplace. Small sellers list products
through Olist, and Olist handles the storefront and logistics. In 2018 the
company published an anonymised extract of real orders placed on the platform
between 2016 and 2018 — roughly 100,000 orders.

**Download size:** around 45 MB compressed.

This is genuine commercial transaction data, which is exactly why it is
valuable for a portfolio project. Real data carries real mess: missing values,
inconsistent records, and edge cases you have to make defensible decisions
about. That decision-making is what employers are actually assessing.

### Licence

Published under **CC BY-NC-SA 4.0**. You may use it for a non-commercial
portfolio project with attribution. The raw CSVs are excluded from this
repository by `.gitignore` — the licence and file size both favour documenting
the download instead of redistributing the data.

---

## 2. How to download

### Option A — Browser download (recommended, simplest)

1. Create a free Kaggle account at https://www.kaggle.com if you do not have one.
2. Open https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
3. Click **Download** (top right). You will get a single ZIP file, typically
   saved to `~/Downloads` as `archive.zip` or
   `brazilian-ecommerce.zip`.
4. Extract the CSV files directly into this project's `dataset/raw/` folder.

In Terminal, adjusting the ZIP filename to match what you actually got:

```bash
cd /path/to/RetailPulse      # the project root
unzip ~/Downloads/archive.zip -d dataset/raw/
ls -lh dataset/raw/
```

`-d dataset/raw/` tells `unzip` where to put the contents. If the extraction
creates a nested subfolder instead of loose CSVs, flatten it:

```bash
cd /path/to/RetailPulse      # the project root
find dataset/raw -name "*.csv" -exec mv {} dataset/raw/ \;
```

### Option B — Kaggle CLI (useful if you will download more datasets later)

```bash
pip install kaggle
```

Then create an API token: Kaggle → your profile picture → **Settings** →
**API** → **Create New Token**. This downloads `kaggle.json`. Install it:

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

`chmod 600` restricts the file to your user only — the Kaggle CLI refuses to
run if the token is world-readable, because it is a credential. Note that
`kaggle.json` is listed in this project's `.gitignore`; never commit it.

Then:

```bash
cd /path/to/RetailPulse      # the project root
kaggle datasets download -d olistbr/brazilian-ecommerce -p dataset/raw --unzip
```

---

## 3. Where files must end up

```
RetailPulse/
└── dataset/
    └── raw/
        ├── olist_customers_dataset.csv
        ├── olist_geolocation_dataset.csv
        ├── olist_order_items_dataset.csv
        ├── olist_order_payments_dataset.csv
        ├── olist_order_reviews_dataset.csv
        ├── olist_orders_dataset.csv
        ├── olist_products_dataset.csv
        ├── olist_sellers_dataset.csv
        └── product_category_name_translation.csv
```

CSVs must sit **directly inside `dataset/raw/`**, not in a subfolder, because
every notebook and script in this project resolves paths relative to
`dataset/raw/`.

> ⚠️ The file list above is the **expected** contents based on the dataset's
> public description. It has **not yet been verified against your actual
> download**. Confirming the real file names, row counts, and columns is task
> 1.12–1.13 in the tracker, and the data dictionary will be built from that
> inspection — not from this list. If your download differs, the inspection
> output is what we trust.

---

## 4. Verify the download

Once extracted, run:

```bash
cd /path/to/RetailPulse      # the project root
ls -lh dataset/raw/*.csv
wc -l dataset/raw/*.csv
```

`ls -lh` shows file sizes in human-readable form; `wc -l` counts lines, which
is roughly row count plus one for the header. Share that output and the
inspection phase begins.

---

## 5. What the files represent

A plain-English view of the table relationships, to be confirmed during
inspection:

- **orders** — one row per order: who placed it, its status, and timestamps
  for purchase, approval, shipping, delivery, and the *estimated* delivery
  date. The gap between estimated and actual delivery is the basis for all
  delivery performance analysis.
- **order_items** — one row per *product within an order*. An order containing
  three products produces three rows here. This table holds `price` and
  `freight_value`, making it the foundation of revenue calculation.
- **customers** — the buyer, their city, state, and zip prefix. Contains two
  ID columns that behave very differently; see the warning below.
- **products** — product attributes: category, dimensions, weight, photo count.
- **sellers** — seller location.
- **order_payments** — payment records. One order can have several rows
  (instalments, or multiple payment methods).
- **order_reviews** — review score of 1–5 plus optional Portuguese comment
  text, linked to an order.
- **product_category_name_translation** — maps Portuguese category names to
  English. Needed for readable dashboards.
- **geolocation** — zip prefix to latitude/longitude. Optional; useful for map
  visuals.

### ⚠️ The single most important detail in this dataset

The customers table contains **two** identifier columns:

- `customer_id` — a *new value for every order*. The same human buying twice
  gets two different `customer_id` values.
- `customer_unique_id` — the stable identifier for the actual person.

Using `customer_id` to count customers makes every customer look brand new,
which silently destroys repeat-purchase rate, retention, cohort analysis, and
RFM segmentation. Nearly every beginner project online gets this wrong.

**Rule for this project:** counting customers or analysing repeat behaviour
uses `customer_unique_id`. Joining to orders uses `customer_id`. This is
recorded in the data dictionary and the methodology document.

---

## 6. Common problems

| Problem | Cause | Fix |
|---|---|---|
| Kaggle asks you to sign in | Download requires a free account | Create one; no payment needed |
| ZIP extracted into a nested folder | Archive structure varies | Use the `find ... -exec mv` command in Option A |
| `kaggle: command not found` | CLI not installed or not on PATH | Use Option A instead |
| `403 Forbidden` from the CLI | Token missing, stale, or wrongly placed | Re-create `kaggle.json`, confirm it is at `~/.kaggle/kaggle.json` with `chmod 600` |
| Garbled characters in review text | Portuguese accents read with the wrong encoding | Load with `encoding='utf-8'` in pandas; handled in Phase 3 |
