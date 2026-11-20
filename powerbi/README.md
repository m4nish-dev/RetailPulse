# Phase 6 — Power BI Dashboards

> ## 🚧 STATUS: NOT COMPLETE — BLOCKED ON ENVIRONMENT
>
> **No `.pbix` file exists, and no dashboard has been built or tested.**
>
> Power BI Desktop runs only on Windows. This machine is macOS 15.8.1 on
> Apple Silicon, and the environment was checked directly on 2026-11-13:
>
> | Checked for | Result |
> |---|---|
> | Power BI Desktop | not installed |
> | Parallels Desktop / VMware Fusion / UTM / VirtualBox | none installed |
> | CrossOver / Whisky / wine | none installed |
> | Docker / QEMU | none installed |
> | Any existing `.pbix` on the machine | none found |
>
> Everything in this folder is **preparation**: assets that are
> platform-independent and have been validated as far as macOS allows. The
> dashboard itself is outstanding.

---

## What IS done, and what was actually verified

| Asset | Status | How it was verified |
|---|---|---|
| `RetailPulse_Theme.json` | ✅ Complete | Parsed as JSON; all 8 hex values well-formed; palette passes colour-vision checks on the dark surface (worst adjacent pair ΔE 8.4 protan, all ≥ 3:1 contrast) |
| `dax_measures.md` — 84 measures | ✅ Logic verified, audited 2026-11-20 | `scripts/validate_dax_logic.py` — **230/230 checks PASS**, every measure covered; 15 of the original 49 corrected. See [`dax_measure_audit.md`](dax_measure_audit.md) |
| `data_model.md` | ✅ Complete | Relationships and cardinality derived from Phase 1's validated key analysis |
| `dashboard_specification.md` | ✅ Complete | Six pages specified visual by visual, every KPI naming a verified measure |
| `data/` — 11 CSV extracts | ✅ Regenerated 2026-11-20 | 335,797 rows, 49 MB, exported from the validated views; now include the Phase 2 flags (`carrier_before_approval`, `stage_timing_valid`, `review_before_delivery`). All other values byte-identical to the 2026-11-13 export |
| `data/analytical/` — 6 analytical sources + `dim_category` + `seller_scorecard` | ✅ Built and validated 2026-11-20 | RFM, cohort matrix, product and seller × category drill-through, delivery stages, category satisfaction, seller counts. `scripts/validate_powerbi_sources.py` **90/90 PASS** — see [`analytical_sources.md`](analytical_sources.md) |
| **The `.pbix` dashboard** | ❌ **Not built** | **Requires Windows** |

### ⚠ What "230/230 PASS" does and does not mean

`scripts/validate_dax_logic.py` emulates each measure's logic in pandas over
the CSVs Power BI imports, including its filter behaviour, and compares it in
several filter contexts with an independent SQL answer from the base tables.
No expected value is typed in.

- ✅ **Verified:** filter context, grain, denominator, arithmetic — whether
  each measure asks the right question of the right rows.
- ❌ **Not verified:** DAX syntax, `CALCULATE` evaluation at runtime, and
  behaviour under slicer interaction.

**A PASS means "this will produce the right number if the DAX is typed
correctly", not "this has been run in Power BI."**

> The check earned its place immediately: it caught a hand-written expected
> value for eligible freight (2,237,474.78) that had never been computed.
> The true figure is **2,241,126.29**.

---

## What is needed to finish

**One Windows environment with Power BI Desktop.** Nothing else is missing —
the data, the measures, the model and the page specifications are all ready.

| Route | Cost | Setup | Notes |
|---|---|---|---|
| **UTM** (free, Apple Silicon) | Free | 2–4 hours | Windows 11 ARM; Power BI runs under emulation, slower but workable |
| **Parallels Desktop** | ~$100/yr | ~1 hour | Smoothest on Apple Silicon |
| **Cloud Windows VM** (Azure/AWS) | ~$0.10–0.50/hr | ~30 min | No local install; pay only while building |
| Power BI Service (browser) | Free | minutes | ⚠ **Partial only** — web authoring cannot produce a `.pbix`, and DAX/modelling are restricted. Not sufficient for this specification |

**Recommendation:** a real VM. Power BI plus DAX is frequently a hard filter
in Data Analyst screening, and a working `.pbix` with verified measures is
worth considerably more than a screenshot of something else.

---

## Build sequence, once Windows is available

### 1. Get the data across

Either copy `powerbi/data/` to the Windows machine (turnkey, no database
needed), or connect Power BI directly to MySQL — better long-term, because
Refresh then re-reads the live views:

```
Get Data ▸ MySQL database
  Server:   <mac-ip>:3306     (or localhost if MySQL runs on the VM)
  Database: retailpulse
```

MySQL would need to accept connections from the VM, and `root` currently has
no password (see `documentation/mysql_setup.md` §2). **Set a password before
exposing the port.** For a one-off build, the CSVs avoid the issue entirely.

If `powerbi/data/` is absent, regenerate it:
```bash
./venv/bin/python scripts/export_powerbi_data.py      # the 7 views + dim_date
./venv/bin/python scripts/export_powerbi_sources.py   # data/analytical/ (read-only SQL)
./venv/bin/python scripts/validate_powerbi_sources.py # 90 checks
./venv/bin/python scripts/validate_dax_logic.py       # 230 checks; writes dax_validation_results.csv
./venv/bin/python scripts/build_dax_audit.py          # regenerates dax_measure_audit.md
```

### 2. Build the model
Follow [`data_model.md`](data_model.md): load the 7 views + `dim_date` and the
analytical sources in `data/analytical/`, create the relationships (3
original + 7 for the analytical sources, set **one-to-many, single
direction**), **mark `dim_date` as the date table**, set
column formats, and set "Don't summarize" on every ID column.

### 3. Apply the theme
View ▸ Themes ▸ Browse for themes ▸ `RetailPulse_Theme.json`

### 4. Create the measures
Add a blank `_Measures` table, then paste from
[`dax_measures.md`](dax_measures.md).

### 5. Build the six pages
Follow [`dashboard_specification.md`](dashboard_specification.md). **The
mandatory captions in that document are not optional polish** — without them
several pages are actively misleading (inherited seller ratings, historical
vs predicted customer value, correlation vs causation, the padded on-time
baseline).

### 6. Test before declaring it done

**Measure values** — each card must read exactly:

| Measure | Expected |
|---|---|
| Total Revenue | 13,494,400.74 |
| Total Orders | 99,441 |
| Total Customers | **96,096** (99,441 means it is counting `customer_id` — wrong) |
| Average Order Value | 137.42 |
| Delivery Denominator | **96,476** (not 96,478) |
| Late Orders | 7,827 |
| On-Time Rate | 91.89% |
| Avg Review Score | 4.0864 |
| Total Freight | 2,241,126.29 |

**Also test:**
- [ ] Category revenue sums to Total Revenue across Page 3
- [ ] Seller revenue sums to Total Revenue across Page 4
- [ ] Every slicer filters the page it sits on
- [ ] Cross-filtering within each page behaves sensibly
- [ ] Drill-through works on Pages 3 and 4
- [ ] Trend visuals are filtered to the stable window and show no cliff at
      either end
- [ ] Currency displays as R$ with 2 dp everywhere
- [ ] No visual is blank or shows an error
- [ ] All mandatory captions are present and readable
- [ ] Refresh completes with no warnings

Record the results, then capture screenshots into
`reports/dashboard_screenshots/`.

---

## Why Power BI was not replaced with another tool

Substituting Tableau Public, Metabase or a web dashboard would produce
something that *looks* finished while quietly changing what the project
claims. Power BI with DAX is a specific, commonly-required skill, and the
honest position is that this phase is **blocked on hardware, not on
analysis**.

The work that does not depend on the tool — the model design, the measure
logic, the page specifications — is complete and verified.

---

## Files

| File | Contents |
|---|---|
| `RetailPulse_Theme.json` | Power BI theme: charcoal / white / orange, CVD-validated |
| `dax_measures.md` | 84 measures, logic verified (230/230 checks) |
| `dax_measure_audit.md` | Generated audit: every measure, its status, what changed and the evidence |
| `dax_validation_results.csv` | Every validation check with model value, expected value and context |
| `data_model.md` | Tables, relationships, cardinality, formatting, Import rationale |
| `dashboard_specification.md` | Six pages, visual by visual, with mandatory captions |
| `data/` | 11 CSV extracts + generated `dim_date` (gitignored — 49 MB, regenerable) |
| `data/analytical/` | 8 analytical source CSVs + `_manifest.csv` (gitignored — 23 MB, regenerable) |
| `analytical_sources.md` | Grain, columns, logic, relationships, limitations and validation of the analytical sources |
| `RetailPulse.pbix` | **Does not exist yet** |
