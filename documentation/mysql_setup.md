# MySQL Setup Guide

How the `retailpulse` database was created, how to recreate it, and what you
need to do about security.

---

## 1. Which MySQL, and why

**Installed: MySQL 8.4 LTS** via Homebrew (`mysql@8.4`).

This needed a deliberate choice. Plain `brew install mysql` would have
installed **MySQL 26.10** — far beyond the MySQL 8 this project targets. The
available options were:

| Formula | Version | Verdict |
|---|---|---|
| `mysql` | 26.10.0 | ❌ Not MySQL 8 |
| `mysql@8.4` | 8.4.13 | ✅ **Chosen** — MySQL 8, current LTS, supported |
| `mysql@8.0` | 8.0.46 | ❌ MySQL 8, but reached end-of-life April 2026 |

8.4 is the Long Term Support release of the MySQL 8 line, so it is both what
the project asked for and still receiving security fixes.

```bash
brew install mysql@8.4
brew services start mysql@8.4
```

### `mysql@8.4` is "keg-only"

Homebrew does not put versioned formulae on your `PATH`, because they would
clash with a different MySQL version. So `mysql` alone will not work — use the
full path, or add it to your shell:

```bash
# full path (what this project's commands use)
/opt/homebrew/opt/mysql@8.4/bin/mysql -u root

# or add to PATH permanently
echo 'export PATH="/opt/homebrew/opt/mysql@8.4/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## 2. Security: two accounts, least privilege (updated in Phase 5)

| Account | Used for | Privileges |
|---|---|---|
| `retailpulse_app` | **every script, validator and notebook** (via `scripts/rp_db.py` and `.env`) | `SELECT` on `retailpulse.*` only. No writes, no DDL, no other schemas, no `FILE`, no `GRANT` |
| an administrator (`root` locally) | the one-off rebuild in §3 and creating the app account | full |

The application account was tested (Phase 5): reads succeed; `INSERT`,
`UPDATE`, `DELETE`, `CREATE TABLE`, `DROP VIEW`, `DROP DATABASE`, reading
`mysql.user`, `SELECT ... INTO OUTFILE` and `CREATE USER` are all refused.
`scripts/rp_db.py` refuses `MYSQL_USER=root` outright and marks every session
`READ ONLY` as a second barrier.

**Credentials live only in `.env`** (git-ignored, mode 600), copied from
`.env.example`. No password appears in any SQL file, script, notebook or log;
`sql/10_app_user.sql` holds a placeholder only.

### ⚠ `root` still has no password

A fresh Homebrew MySQL creates `root@localhost` **with an empty password**.
Application code no longer uses it, but the account itself is unchanged:
setting a root password is your decision. The server listens on `127.0.0.1`
only, so the risk is limited to other users of this machine. To secure it:

```bash
/opt/homebrew/opt/mysql@8.4/bin/mysql_secure_installation
```

After that, the admin commands in §3 need `-p`. For convenience you can keep
admin credentials in `~/.my.cnf` **outside this repository** (`chmod 600`).
Application scripts are unaffected: they use `.env`.

---

## 3. Build the database from scratch

Run these **from the project root**, in order. The import script uses relative
paths, so your working directory matters.

```bash
cd /path/to/RetailPulse      # the project root
MYSQL=/opt/homebrew/opt/mysql@8.4/bin/mysql

# 1. Create the database, 9 tables, keys and indexes
$MYSQL -u root < sql/01_schema.sql

# 2. Bulk-load the cleaned CSVs  (--local-infile=1 is required)
$MYSQL --local-infile=1 -u root retailpulse < sql/02_import.sql

# 3. Create the 7 reusable views
$MYSQL -u root retailpulse < sql/07_business_analysis.sql

# 4. Create the read-only application account (once). Edit a COPY of
#    sql/10_app_user.sql in your session, or paste its statements into
#    `$MYSQL -u root`, replacing REPLACE_WITH_PASSWORD with a long random
#    password. Never save the real password into the file.
#    python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 5. Put that password in .env (from .env.example), then verify as the app account
cp .env.example .env && chmod 600 .env       # edit MYSQL_PASSWORD
python scripts/rp_db.py                      # connection self-test
python scripts/run_all_validations.py        # includes sql/08_validation.sql (71 checks)
```

**Prerequisite:** `dataset/cleaned/` must contain the 9 cleaned CSVs. They are
not in Git (90 MB derived artifact). Regenerate with
`notebooks/02_data_cleaning.ipynb` — see `dataset/cleaned/README.md`.

---

## 4. `local_infile` — the setting that trips everyone up

`LOAD DATA LOCAL INFILE` reads a file from the **client** machine and streams
it to the server. MySQL disables this by default on both sides, because a
malicious server could otherwise ask your client for arbitrary local files.

It must be enabled in **two** places:

| Side | How |
|---|---|
| Server | `SET GLOBAL local_infile = 1;` — near the top of `02_import.sql` |
| Client | the `--local-infile=1` flag on the `mysql` command |

Since 2026-11-27, `02_import.sql` ends with `SET GLOBAL local_infile = 0;`, so
the server setting is only on during the import. **On this machine it is still
on from the earlier imports.** Turn it off once as an administrator:
`mysql -u root -e "SET GLOBAL local_infile = 0;"` (add `SET PERSIST` instead of
`SET GLOBAL` to keep it off across server restarts). Nothing in the project
needs it outside an import.

Miss either one and you get:

```
ERROR 3948 (42000): Loading local data is disabled;
this must be enabled on both the client and server sides
```

The setting is not persistent — it resets when the server restarts, which is
why `02_import.sql` sets it each time rather than relying on a config file.

---

## 5. Why `LOAD DATA` and not `INSERT`

`LOAD DATA` is MySQL's bulk loader. It streams a file straight into the
storage engine instead of parsing 569,776 separate `INSERT` statements —
roughly two orders of magnitude faster here, and what you would use in a real
job.

### Five things that break a naive load, and how the script handles each

| Problem | What goes wrong | Fix used |
|---|---|---|
| **Newlines inside review text** | 3,852 comments contain a newline because customers pressed Enter. The loader treats each as a row break and the import shatters | `FIELDS ENCLOSED BY '"'` |
| **Booleans written as text** | pandas exports `True`/`False`, not `1`/`0`. Loading `'True'` into TINYINT silently yields **0** — every flag reads false | `CASE @v WHEN 'True' THEN 1 ...` |
| **Empty strings are not NULL** | A blank CSV field arrives as `''`, which becomes `0000-00-00` in a DATETIME | `NULLIF(@v, '')` |
| **Integers written as floats** | pandas writes a nullable int column as `'40.0'`; loading into SMALLINT truncates with a warning | `ROUND(NULLIF(@v, ''))` |
| **Leading zeros in zip codes** | `'01037'` as an INT becomes `1037` — a different, wrong place | Schema uses `CHAR(5)`, not INT |

The script loads every CSV column into a `@variable` and then uses `SET` to
transform it. That is the standard way to clean data during a bulk load.

---

## 6. Import limitations, stated openly

**Column subsets are imported, not whole CSVs.** `orders_clean.csv` has 36
columns; the `orders` table stores 21. The 15 omitted are either:

- duplicated from `customers` (`customer_state`, `customer_city`,
  `customer_zip_code_prefix`), or
- aggregates of child tables (`order_revenue`, `item_count`, `review_count`,
  `payment_total`, …)

Storing an aggregate in `orders` would duplicate data that can drift out of
sync with its source. The views in `07_business_analysis.sql` compute them
instead, so they are always correct by construction.

**No ROW is dropped — only redundant columns are not copied.** Row counts are
verified against the CSVs in `08_validation.sql`.

**One row is added deliberately.** The category lookup loads 73 rows from CSV,
then `02_import.sql` inserts a single `'unknown' → 'unknown'` sentinel so the
610 products with no category can satisfy a real `FOREIGN KEY` rather than
forcing the constraint to be dropped. 73 + 1 = 74, verified.

**`geolocation` has no foreign key.** Customer and seller zip prefixes are not
a perfect subset of the geolocation prefixes, and it is reference data for
maps that no KPI depends on, so a constraint would add friction for no benefit.

---

## 7. Useful commands

```bash
MYSQL=/opt/homebrew/opt/mysql@8.4/bin/mysql

# interactive, read-only session as the app account (prompts for the .env password)
$MYSQL -u retailpulse_app -p -h 127.0.0.1 retailpulse

# one-off query
$MYSQL -u retailpulse_app -p -h 127.0.0.1 retailpulse -e "SELECT COUNT(*) FROM orders;"

# run an analysis file
$MYSQL -u retailpulse_app -p -h 127.0.0.1 retailpulse --table < sql/05_advanced_sql.sql

# admin only (rebuild, account management)
$MYSQL -u root

# service control
brew services start   mysql@8.4
brew services stop    mysql@8.4
brew services restart mysql@8.4
brew services list
```

### A GUI, if you want one

```bash
brew install --cask mysqlworkbench
```

MySQL Workbench is the standard GUI and is what most SQL job postings assume
familiarity with. Connect to `127.0.0.1:3306` as `retailpulse_app` with the
password from `.env` for read-only exploration.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `command not found: mysql` | `mysql@8.4` is keg-only | Use the full path, or add it to `PATH` (section 1) |
| `ERROR 3948 ... local data is disabled` | `local_infile` off | Add `--local-infile=1` to the client command |
| `ERROR 2002 ... Can't connect ... socket` | Server not running | `brew services start mysql@8.4` |
| `ERROR 1045 Access denied for user 'root'` | A root password was set | Add `-p` and enter it (admin commands only) |
| `CONFIG ERROR: Missing required MySQL setting(s)` | No `.env`, or a value is empty | `cp .env.example .env` and fill it in |
| `CONFIG ERROR: MYSQL_USER is 'root'` | `.env` points at root | Use `retailpulse_app` (§2) |
| `CONFIG ERROR: Cannot connect ... error 1045` | Wrong password in `.env` | Fix `MYSQL_PASSWORD`, or reset it with `ALTER USER` (see `sql/10_app_user.sql`) |
| `ERROR 1142 ... command denied to user 'retailpulse_app'` | A write attempted with the read-only account | Expected: writes are admin-only |
| `File 'dataset/cleaned/...' not found` | Wrong working directory | `cd` to the project root first |
| Row counts short after import | Usually an unquoted newline | Confirm `FIELDS ENCLOSED BY '"'` is present |
| `Data truncated for column ...` warning | Float string into an INT column | Already handled by `ROUND(NULLIF(...))` |

---

## 9. Starting over

```bash
# the schema script drops and recreates the database, so this is all you need
/opt/homebrew/opt/mysql@8.4/bin/mysql -u root < sql/01_schema.sql
```

`01_schema.sql` begins with `DROP DATABASE IF EXISTS retailpulse;`, so
rebuilding is always clean and repeatable. Nothing in `dataset/raw/` or
`dataset/cleaned/` is touched by any SQL in this project.
