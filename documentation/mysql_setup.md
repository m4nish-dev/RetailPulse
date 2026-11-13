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

## 2. ⚠ Security: your MySQL currently has NO root password

A fresh Homebrew MySQL install creates `root@localhost` **with an empty
password**. That is how this project connected — no password was guessed, set,
invented or written into any file.

**I deliberately did not run `mysql_secure_installation`**, because it sets a
root password and that is your decision, not something to be done to your
machine without asking.

### What this means

The server only listens on `localhost`, so it is not reachable from the
network. For a local analytics project on your own laptop this is normal and
low risk.

### If you want to secure it (recommended if this machine is shared)

```bash
/opt/homebrew/opt/mysql@8.4/bin/mysql_secure_installation
```

It will ask you to set a root password and answer a few yes/no prompts. **If
you do this, every command in this guide needs `-p` added**, which will then
prompt you for the password:

```bash
/opt/homebrew/opt/mysql@8.4/bin/mysql -u root -p retailpulse
```

### Never commit credentials

`.gitignore` already excludes `.env`, `*.cnf`, `.my.cnf`, `credentials.json`
and `*.pem`. If you set a password and want to avoid typing it, put it in
`~/.my.cnf` **outside this repository**:

```ini
[client]
user = root
password = your_password
```
```bash
chmod 600 ~/.my.cnf
```

No password appears anywhere in this project's files, and none should.

---

## 3. Build the database from scratch

Run these **from the project root**, in order. The import script uses relative
paths, so your working directory matters.

```bash
cd /Users/manish/Desktop/RetailPulse
MYSQL=/opt/homebrew/opt/mysql@8.4/bin/mysql

# 1. Create the database, 9 tables, keys and indexes
$MYSQL -u root < sql/01_schema.sql

# 2. Bulk-load the cleaned CSVs  (--local-infile=1 is required)
$MYSQL --local-infile=1 -u root retailpulse < sql/02_import.sql

# 3. Create the 7 reusable views
$MYSQL -u root retailpulse < sql/07_business_analysis.sql

# 4. Verify everything against the Python reference
$MYSQL -u root retailpulse < sql/08_validation.sql
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
| Server | `SET GLOBAL local_infile = 1;` — the first line of `02_import.sql` |
| Client | the `--local-infile=1` flag on the `mysql` command |

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

# interactive session
$MYSQL -u root retailpulse

# one-off query
$MYSQL -u root retailpulse -e "SELECT COUNT(*) FROM orders;"

# readable column output for wide results
$MYSQL -u root retailpulse --table -e "SELECT * FROM vw_monthly_revenue LIMIT 5;"

# run an analysis file
$MYSQL -u root retailpulse --table < sql/05_advanced_sql.sql

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
familiarity with. Connect to `127.0.0.1:3306`, user `root`, password blank
(unless you set one in section 2).

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `command not found: mysql` | `mysql@8.4` is keg-only | Use the full path, or add it to `PATH` (section 1) |
| `ERROR 3948 ... local data is disabled` | `local_infile` off | Add `--local-infile=1` to the client command |
| `ERROR 2002 ... Can't connect ... socket` | Server not running | `brew services start mysql@8.4` |
| `ERROR 1045 Access denied for user 'root'` | A password was set | Add `-p` and enter it |
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
