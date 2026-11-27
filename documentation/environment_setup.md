# Environment Setup Guide

Audit of this Mac's toolchain as of 2026-11-12, plus practical alternatives
for the tools that are missing. Nothing here blocks the project.

---

## 1. Current state

| Tool | Status | Needed from |
|---|---|---|
| Python 3.14.3 (Homebrew) | ✅ Installed | Phase 3 |
| Python 3.10 (Homebrew) | ✅ Installed | — |
| Python 3.9 (system, `/usr/bin/python3`) | ✅ Installed | Do not use |
| pip 26.0 | ✅ Installed | Phase 3 |
| Git 2.53.0 | ✅ Installed | Phase 1 |
| pandas / NumPy / Matplotlib | ❌ Missing at the time (Seaborn was planned but never used) | Phase 3 |
| Jupyter Lab | ❌ Missing | Phase 3 |
| MySQL | ❌ Missing | Phase 4 |
| Microsoft Excel | ❌ Missing (Numbers.app present) | Phase 2 |
| Power BI Desktop | ❌ Missing — **not available for macOS** | Phase 6 |
| Kaggle CLI | ❌ Missing (optional) | Phase 1 |

Nothing is needed until its phase arrives, so none of this has to be solved
today.

---

## 2. Python packages (needed in Phase 3)

Install into a **virtual environment**, not system-wide. A virtual environment
is a private folder of packages belonging to this project only. Two reasons it
matters: Homebrew Python blocks system-wide `pip install` to protect itself,
and project-local packages mean a future project needing a different pandas
version cannot break this one.

```bash
cd /path/to/RetailPulse      # the project root
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Your prompt will show `(venv)` once activated. Run `deactivate` to exit, and
re-run the `source` line in each new terminal session. `venv/` is gitignored.

### Which Python version

Your default `python3` is **3.14.3**, which is very new. Data libraries
sometimes lag a few months behind a new Python release in publishing
pre-compiled packages, and without one, pip tries to compile from source —
which usually fails without developer tooling.

We will attempt 3.14 first. If installation errors mention building wheels or
missing compilers, fall back to 3.10, which has universal library support:

```bash
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

This decision is logged in the tracker under Open Decisions.

> **Outcome (verified 2026-11-20).** Python 3.14.3 worked; every pinned package
> installs from a prebuilt wheel. The 3.10 fallback above **no longer applies**:
> the pinned versions require **Python ≥ 3.12** (`numpy==2.5.4` requires
> ≥ 3.12; `pandas==3.1.1` and `matplotlib==3.11.2` ≥ 3.11). Use 3.14 (tested)
> or at least 3.12. A fresh `venv` + `pip install -r requirements.txt` on 3.14
> was re-tested in Phase 5.

---

## 3. Excel alternative (Phase 2)

Excel is not installed. Phase 2 needs pivot tables, so the options are:

| Option | Cost | Pivot tables | Recommendation |
|---|---|---|---|
| **LibreOffice Calc** | Free | Yes — "Pivot Table", functionally equivalent | ✅ **Recommended** |
| Numbers (installed) | Free | Weak — "Categories" only, limited | Workable but frustrating |
| Microsoft 365 trial | Free 1 month, then paid | Yes, the real thing | Only if you want literal Excel |
| Excel on the web | Free with a Microsoft account | Yes, but file-size limits | Likely too limited for these files |

Install LibreOffice:

```bash
brew install --cask libreoffice
```

**A note on file sizes in Phase 2:** the largest file (geolocation,
1,000,163 rows) fits inside Excel's 1,048,576-row sheet limit, but only with
about 48,000 rows of headroom — and a spreadsheet that size is slow and
painful to pivot on a laptop. Phase 2 will therefore work the business-critical
tables by hand (orders, order_items, customers, products, sellers, payments,
reviews — all between 70 and 113,000 rows, perfectly comfortable) and treat
geolocation as a Python-only table, since it is optional map-visual data
rather than a source of business metrics. The report will record the sizes and
the reasoning, which is the real point: knowing where the spreadsheet ceiling
sits and choosing tools deliberately.

For your CV, "LibreOffice Calc" and "Excel" are interchangeable skills —
pivot tables, VLOOKUP/XLOOKUP, and conditional formatting work the same way.
Listing Excel on your resume is fair; the transferable skill is real.

---

## 4. MySQL (Phase 4)

Two sensible routes:

> **Phase 5 update.** The project uses Homebrew **`mysql@8.4`** (see
> `mysql_setup.md`). Application code never connects as root: it uses the
> read-only `retailpulse_app` account (`sql/10_app_user.sql`) with credentials
> in a git-ignored `.env` copied from `.env.example`. `python scripts/rp_db.py`
> tests the connection; `python scripts/run_all_validations.py` runs every check.
> The commands below are the original planning notes.

### Option A — Homebrew (simpler)

```bash
brew install mysql
brew services start mysql
mysql_secure_installation        # set a root password
mysql -u root -p                 # confirm you can connect
```

### Option B — Docker (cleaner isolation, if Docker is already installed)

```bash
docker run --name retailpulse-mysql \
  -e MYSQL_ROOT_PASSWORD=yourpassword \
  -e MYSQL_DATABASE=retailpulse \
  -p 3306:3306 -d mysql:8
```

Also worth installing for writing and browsing queries visually:

```bash
brew install --cask mysqlworkbench
```

MySQL Workbench is the standard GUI and is what most SQL job postings assume
familiarity with. Decide between A and B when Phase 4 begins; nothing before
then depends on it.

---

## 5. Power BI on macOS — the one real constraint

**Power BI Desktop does not exist for macOS.** Microsoft has never released a
Mac version, and there is no workaround within macOS itself. This is a hard
limitation of the platform, not something that can be configured around.

Options, honestly compared:

| Option | Cost | Effort | Gets you a `.pbix`? |
|---|---|---|---|
| **Windows VM via UTM** (Apple Silicon) | Free | Medium — a few hours | ✅ Yes, full Desktop |
| **Parallels Desktop** | ~$100/yr | Low — smoothest experience | ✅ Yes, full Desktop |
| **Cloud Windows VM** (Azure/AWS, hourly) | ~$0.10–0.50/hr | Low | ✅ Yes |
| **Power BI Service** (web, free account) | Free | Low | ⚠️ Partial — web authoring is limited; no local `.pbix` editing, weaker DAX/modelling |
| **Tableau Public** instead | Free | Low — native Mac app | ❌ No, but produces a comparable dashboard portfolio piece |

**Recommendation:** if Power BI specifically appears in the job descriptions
you are targeting — and in India it very often does — invest in a Windows VM.
Power BI plus DAX is frequently a hard filter in Data Analyst screening, and
a real `.pbix` with working DAX measures is worth far more on your resume than
a screenshot of something else.

If you want to defer that decision, Phases 1–5 and 7 produce a complete,
genuinely strong project on their own: cleaned data, a MySQL schema, 25–30
analytical queries, RFM segmentation, cohort analysis, and documented
insights. Phase 6 can be added once the VM is ready. This is also the right
order of operations regardless — the dashboard should be built on validated
data, not before it.

---

## 6. Install-nothing-yet summary

Needed right now: **nothing**. Only the dataset download.

| Phase | Install before starting |
|---|---|
| 1 | Nothing |
| 2 | LibreOffice (`brew install --cask libreoffice`) |
| 3 | Python packages (`pip install -r requirements.txt`) |
| 4 | MySQL + Workbench |
| 5 | Nothing new |
| 6 | Windows environment + Power BI Desktop |
| 7–9 | Nothing |
