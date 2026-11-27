"""
RetailPulse - run every validation in one command (Phase 5).

    python scripts/run_all_validations.py                 # everything, incl. notebooks
    python scripts/run_all_validations.py --skip-notebooks

Runs the project's existing checks in dependency order and prints PASS / FAIL /
SKIP for each, then a total. Exit code 1 if any required check FAILS.

SAFETY
  * Read-only. Every database step uses the read-only application account
    from .env (scripts/rp_db.py). Nothing here can write to MySQL.
  * Never runs destructive or regenerating steps: schema rebuild (sql/01),
    import (sql/02), view recreation (sql/07), account setup (sql/10), the
    cleaning notebook (rewrites dataset/cleaned/) or the CSV exports. They are
    listed as SKIP with the reason.
  * Notebooks are executed into a temporary folder, so the project notebooks
    are not rewritten. (They re-save their charts; unchanged inputs give
    byte-identical PNGs.)
  * The MySQL client receives the password through a temporary 0600 options
    file, never on the command line.

EXPECTED COUNTS
  Each check's count is compared with the baseline below, so a check that
  silently stops running shows up as a FAIL. Update a baseline only when checks
  are intentionally added or removed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from rp_db import ConfigError, get_connection, load_config      # noqa: E402

PY = sys.executable
EXPECTED = {
    "issue_register": 19,          # scripts/verify_issue_register.py
    "mysql_validation": 71,        # sql/08_validation.sql PASS rows
    "tableau_sources": 90,         # scripts/validate_tableau_sources.py (analytical CSVs vs SQL and pandas)
    "tableau_data": 24,            # scripts/check_tableau_data.py (files, MD5, keys, 8 relationships)
    "tableau_calcs": 264,          # scripts/validate_tableau_calcs.py (90 measures vs SQL, Tableau semantics)
    "tableau_workbook": 16,        # scripts/validate_tableau_workbook.py (generated .twb: XSD + registry)
    "insight_evidence": 78,        # scripts/validate_insight_evidence.py
    "repository": 18,              # scripts/check_repository.py (structure, links, references, security)
    "nb03_code_cells": 30,         # notebooks/03 code cells executed
    "nb03_mysql_checks": 15,       # notebooks/03 §G
    "nb04_checks": 10,             # notebooks/04 §D
}
READ_ONLY_SQL = ["03_basic_analysis.sql", "04_joins_and_aggregations.sql", "05_advanced_sql.sql",
                 "06_customer_analytics.sql", "09_dashboard_sources.sql", "11_insight_evidence.sql"]
NEVER_RUN = [("sql/01_schema.sql", "drops and recreates the database (admin rebuild only)"),
             ("sql/02_import.sql", "reloads all tables (admin rebuild only)"),
             ("sql/07_business_analysis.sql", "drops and recreates the views (admin only)"),
             ("sql/10_app_user.sql", "creates the MySQL account (admin, once)"),
             ("notebooks/02_data_cleaning.ipynb", "rewrites dataset/cleaned/"),
             ("scripts/export_tableau_*.py", "overwrite tableau/data/ (the validators compare the files with live SQL and MD5 manifests instead)")]

RESULTS: list[dict] = []
G, R, Y, B, X = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[0m"
if not sys.stdout.isatty():
    G = R = Y = B = X = ""


def record(name, status, detail, secs=0.0, output=""):
    RESULTS.append({"name": name, "status": status, "detail": detail, "secs": secs})
    colour = {"PASS": G, "FAIL": R, "SKIP": Y}[status]
    print(f"  {colour}{status:<4}{X}  {name:<46} {detail}  ({secs:.1f}s)" if secs else
          f"  {colour}{status:<4}{X}  {name:<46} {detail}")
    if status == "FAIL" and output:
        tail = "\n".join(output.strip().splitlines()[-15:])
        print("        " + tail.replace("\n", "\n        "))


def run(cmd, timeout=1800, cwd=ROOT):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    return p.returncode, p.stdout + p.stderr, time.time() - t


def mysql_client():
    for cand in (os.environ.get("MYSQL_CLIENT"), shutil.which("mysql"),
                 "/opt/homebrew/opt/mysql@8.4/bin/mysql", "/usr/local/opt/mysql@8.4/bin/mysql"):
        if cand and Path(cand).exists():
            return cand
    return None


def run_sql_file(client, cfg, path):
    """Run a .sql file as the app account; password via a temporary 0600 option file."""
    fd, opt = tempfile.mkstemp(prefix="rp_mysql_", suffix=".cnf")
    try:
        os.chmod(opt, 0o600)
        esc = cfg.password.replace("\\", "\\\\").replace('"', '\\"')
        with os.fdopen(fd, "w") as f:
            f.write(f'[client]\nuser="{cfg.user}"\npassword="{esc}"\nhost="{cfg.host}"\nport={cfg.port}\n')
        t = time.time()
        with open(path, "rb") as sql_in:
            p = subprocess.run([client, f"--defaults-extra-file={opt}", "--batch", cfg.database],
                               stdin=sql_in, capture_output=True, timeout=1800)
        out = (p.stdout + p.stderr).decode("utf-8", "replace").replace(cfg.password, "***")
        return p.returncode, out, time.time() - t
    finally:
        os.remove(opt)


def parse_checks(out):
    m = re.findall(r"checks:\s*(\d+)\s+PASS:\s*(\d+)\s+FAIL:\s*(\d+)", out)
    return tuple(map(int, m[-1])) if m else None


def count_status(name, key, total, passed, failed, secs, out, rc):
    exp = EXPECTED[key]
    if rc == 0 and failed == 0 and passed == total == exp:
        record(name, "PASS", f"{passed}/{total} (expected {exp})", secs)
    else:
        record(name, "FAIL", f"{passed}/{total} passed, {failed} failed, exit {rc} (expected {exp}/{exp})", secs, out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--skip-notebooks", action="store_true", help="skip executing notebooks 03 and 04")
    args = ap.parse_args()
    print(f"{B}RetailPulse — full validation run{X}  ({time.strftime('%Y-%m-%d %H:%M')})\n")

    # 1 ---- configuration and connection -----------------------------------
    print(f"{B}1. Configuration{X}")
    cfg = None
    try:
        cfg = load_config()
        conn = get_connection()
        cur = conn.cursor(); cur.execute("SELECT CURRENT_USER(), @@session.transaction_read_only")
        who, ro = cur.fetchone(); conn.close()
        ok = not who.lower().startswith("root@") and ro == 1
        record("MySQL connection via .env (app account)", "PASS" if ok else "FAIL",
               f"connected as {who}, read-only session = {bool(ro)}")
    except ConfigError as e:
        record("MySQL connection via .env (app account)", "FAIL", str(e))

    # 2 ---- data-quality issue register (raw data) -------------------------
    print(f"\n{B}2. Data-quality issue register{X}")
    if not any((ROOT / "dataset" / "raw").glob("*.csv")):
        record("Issue register (dataset/raw)", "SKIP", "dataset/raw/ has no CSV files — see documentation/dataset_setup.md")
    else:
        rc, out, s = run([PY, "-I", "scripts/verify_issue_register.py"])
        m_ok = re.search(r"Counts matching\s*:\s*(\d+)", out); m_bad = re.search(r"MISMATCHES\s*:\s*(\d+)", out)
        m_tot = re.search(r"Issues verified\s*:\s*(\d+)", out)
        if m_ok and m_bad and m_tot:
            count_status("Issue register (recomputed from raw)", "issue_register", int(m_tot[1]), int(m_ok[1]),
                         int(m_bad[1]), s, out, rc)
        else:
            record("Issue register (recomputed from raw)", "FAIL", f"could not read result (exit {rc})", s, out)

    # 3-4 ---- SQL ------------------------------------------------------------
    print(f"\n{B}3. MySQL validation and SQL execution (read-only account){X}")
    client = mysql_client()
    if cfg is None:
        for n in ["sql/08_validation.sql"] + [f"sql/{f}" for f in READ_ONLY_SQL]:
            record(n, "FAIL", "no valid MySQL configuration (see step 1)")
    elif client is None:
        for n in ["sql/08_validation.sql"] + [f"sql/{f}" for f in READ_ONLY_SQL]:
            record(n, "FAIL", "mysql client not found — install it or set MYSQL_CLIENT=/path/to/mysql")
    else:
        rc, out, s = run_sql_file(client, cfg, ROOT / "sql" / "08_validation.sql")
        p, f = len(re.findall(r"\bPASS\b", out)), len(re.findall(r"\bFAIL\b", out))
        errs = re.findall(r"^ERROR \d+.*$", out, flags=re.M)
        if errs:
            record("sql/08_validation.sql", "FAIL", f"SQL error: {errs[0][:120]}", s, out)
        else:
            count_status("sql/08_validation.sql", "mysql_validation", p + f, p, f, s, out, rc)
        for name in READ_ONLY_SQL:
            rc, out, s = run_sql_file(client, cfg, ROOT / "sql" / name)
            errs = re.findall(r"^ERROR \d+.*$", out, flags=re.M)
            record(f"sql/{name} executes", "PASS" if rc == 0 and not errs else "FAIL",
                   "no errors" if rc == 0 and not errs else (errs[0][:120] if errs else f"exit {rc}"), s, out)

    # 5-6 ---- Tableau data, calculated fields, insight evidence ---------------
    print(f"\n{B}4. Tableau data sources, calculated fields, insight evidence{X}")
    for script, key, label in [("validate_tableau_sources.py", "tableau_sources", "Tableau analytical sources (vs SQL + pandas)"),
                               ("check_tableau_data.py", "tableau_data", "Tableau data readiness (files, MD5, keys, relationships)"),
                               ("validate_tableau_calcs.py", "tableau_calcs", "Tableau calculated fields (90 measures, logic)"),
                               ("validate_tableau_workbook.py", "tableau_workbook", "Tableau workbook (generated .twb: XSD + registry)"),
                               ("validate_insight_evidence.py", "insight_evidence", "Insight evidence (sql/11 vs pandas)")]:
        rc, out, s = run([PY, f"scripts/{script}"])
        res = parse_checks(out)
        if res:
            count_status(label, key, res[0], res[1], res[2], s, out, rc)
        else:
            record(label, "FAIL", f"could not read result (exit {rc})", s, out)

    # 7 ---- notebooks ---------------------------------------------------------
    print(f"\n{B}5. Notebooks{X}")
    if args.skip_notebooks:
        record("notebooks/03_exploratory_data_analysis.ipynb", "SKIP", "--skip-notebooks")
        record("notebooks/04_data_quality_investigation.ipynb", "SKIP", "--skip-notebooks")
    else:
        with tempfile.TemporaryDirectory(prefix="rp_nb_") as tmp:
            for nb, checks in [("03_exploratory_data_analysis", [("Checks: (\\d+)\\s+PASS: (\\d+)\\s+FAIL: (\\d+)", "nb03_mysql_checks")]),
                               ("04_data_quality_investigation", [("PASS (\\d+) / (\\d+)", "nb04_checks")])]:
                rc, out, s = run([PY, "-m", "nbconvert", "--to", "notebook", "--execute",
                                  "--output-dir", tmp, "--output", f"{nb}.ipynb",
                                  "--ExecutePreprocessor.timeout=1800", f"{nb}.ipynb"], cwd=ROOT / "notebooks")
                label = f"notebooks/{nb}.ipynb"
                if rc != 0:
                    record(label, "FAIL", "execution error", s, out)
                    continue
                data = json.load(open(Path(tmp) / f"{nb}.ipynb"))
                code = [c for c in data["cells"] if c["cell_type"] == "code"]
                n_exec = sum(1 for c in code if c.get("execution_count"))
                n_err = sum(o.get("output_type") == "error" for c in code for o in c.get("outputs", []))
                text = "".join("".join(o.get("text", "")) for c in code for o in c.get("outputs", []))
                problems, notes = [], [f"{n_exec}/{len(code)} code cells"]
                if n_err or n_exec != len(code):
                    problems.append(f"{n_err} errors")
                if nb.startswith("03") and len(code) != EXPECTED["nb03_code_cells"]:
                    problems.append(f"expected {EXPECTED['nb03_code_cells']} code cells")
                for pat, key in checks:
                    m = re.findall(pat, text)
                    if not m:
                        problems.append("check summary not found")
                        continue
                    vals = list(map(int, m[-1]))
                    passed, total = (vals[1], vals[0]) if len(vals) == 3 else (vals[0], vals[1])
                    failed = vals[2] if len(vals) == 3 else total - passed
                    notes.append(f"{passed}/{total} checks")
                    if failed or passed != EXPECTED[key] or total != EXPECTED[key]:
                        problems.append(f"expected {EXPECTED[key]}/{EXPECTED[key]} checks")
                record(label, "FAIL" if problems else "PASS",
                       ", ".join(notes + problems) + ("" if problems else " (executed in a temp folder)"), s, out)

    # ---- repository, documentation and security ---------------------------------
    print(f"\n{B}6. Repository: structure, links, references, security{X}")
    rc, out, secs = run([PY, "scripts/check_repository.py"])
    res = parse_checks(out)
    if res:
        count_status("Repository checks (links, paths, secrets, ignores)", "repository", res[0], res[1], res[2], secs, out, rc)
    else:
        record("Repository checks (links, paths, secrets, ignores)", "FAIL", f"could not read result (exit {rc})", secs, out)

    # ---- never run ------------------------------------------------------------
    print(f"\n{B}7. Deliberately not run (destructive or regenerating){X}")
    for name, why in NEVER_RUN:
        record(name, "SKIP", why)

    # ---- total ------------------------------------------------------------------
    n = {k: sum(r["status"] == k for r in RESULTS) for k in ("PASS", "FAIL", "SKIP")}
    print(f"\n{B}TOTAL:{X} {G}{n['PASS']} PASS{X} · {R}{n['FAIL']} FAIL{X} · {Y}{n['SKIP']} SKIP{X}")
    print(f"{G}ALL REQUIRED CHECKS PASSED{X}" if n["FAIL"] == 0 else f"{R}VALIDATION FAILED{X}")
    sys.exit(1 if n["FAIL"] else 0)


if __name__ == "__main__":
    main()
